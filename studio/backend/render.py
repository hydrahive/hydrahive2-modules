"""Film als MP4 rendern (Spec „Bauplan 4d“): Auftrag im Hintergrund, Fortschritt, Ablage studio/renders/.

Die Schnittfassung wird beim Start gelesen (Revision in der Begleitdatei). ffmpeg läuft als Kindprozess mit
Zeitgrenze; der Fortschritt kommt aus `-progress pipe:1` (out_time_us). Behalten werden die letzten KEEP Filme.
"""
from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
import time
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

from . import jobs, plan, render_args, timeline
from ._sources import AUDIO_EXT, IMAGE_EXT, VIDEO_EXT
from ._store import is_id, new_id, project_root, read_json, root, safe_rel, write_json

logger = logging.getLogger("hhmod_studio.render")

KEEP = 10
RENDER_DIR = "studio/renders"


class RenderFailed(RuntimeError):
    """ffmpeg fehlt, bricht ab oder überschreitet die Zeitgrenze."""


def _has_audio(path) -> bool:
    try:
        out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0",
                              str(path)], capture_output=True, text=True, timeout=30, check=False)
        return bool(out.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        return False


def _run_ffmpeg(cmd: list[str], seconds: float, progress: Callable[[float], None]) -> None:
    if not shutil.which(cmd[0]):
        raise RenderFailed()
    limit = render_args.time_limit(seconds)
    started = time.monotonic()
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    except OSError as e:
        raise RenderFailed() from e
    try:
        for line in proc.stdout or []:
            if line.startswith("out_time_us=") and seconds > 0:
                try:
                    progress(min(0.99, int(line.split("=", 1)[1]) / 1e6 / seconds))
                except ValueError:
                    pass
            if time.monotonic() - started > limit:
                proc.kill()
                raise RenderFailed()
        code = proc.wait(timeout=max(5, limit - (time.monotonic() - started)))
    except subprocess.TimeoutExpired as e:
        proc.kill()
        raise RenderFailed() from e
    if code != 0:
        logger.warning("Studio-Film: ffmpeg Code %s: %s", code, (proc.stderr.read() if proc.stderr else "")[-800:])
        raise RenderFailed()


def _segments(pid: str, clips: list[dict]) -> list[dict]:
    def exists(rel: str) -> bool:
        return bool(safe_rel(pid, rel, IMAGE_EXT | VIDEO_EXT))
    segs = render_args.segments(clips, exists=exists)
    for s in segs:
        if s["kind"] == "video":
            s["has_audio"] = _has_audio(project_root(pid) / s["media"])
    return segs


def _audio(pid: str, tl: dict) -> list[dict]:
    sound = [c for t in tl["tracks"] if t["kind"] == "audio" for c in t["clips"]]
    return render_args.audio_parts(sound, exists=lambda rel: bool(safe_rel(pid, rel, AUDIO_EXT)))


def start(pid: str) -> dict:
    tl = timeline.load(pid)
    clips = timeline.clips_of(tl)
    if not clips and not _audio(pid, tl):          # nur gelöschter Ton ergäbe einen Film der Länge 0
        raise plan.PlanError("studio_render_empty")
    size = render_args.frame_size(plan.get_head(pid)["aspect_ratio"])

    def work(progress: jobs.Progress) -> dict:
        sound = _audio(pid, tl)
        lost = sum(1 for c in timeline.all_clips(tl) if c["kind"] == "audio") - len(sound)
        segs = render_args.pad_to(_segments(pid, clips), render_args.audio_end(sound))
        seconds = render_args.total_seconds(segs)
        name = f"{new_id()}.mp4"
        out_dir = root(pid, create=True) / "renders"
        out_dir.mkdir(parents=True, exist_ok=True)
        tmp = out_dir / f".{name}.part.mp4"
        with tempfile.TemporaryDirectory(prefix="studio-render-") as td:
            texts = {}
            for i, s in enumerate(segs):
                if s["kind"] == "placeholder" and render_args.label_text(s.get("label", "")):
                    texts[i] = Path(td) / f"{i}.txt"
                    texts[i].write_text(render_args.wrap(render_args.label_text(s["label"]), size), encoding="utf-8")
            cmd = render_args.command(segs, project_root(pid), tmp, size=size, fps=tl["fps"], text_files=texts, audio=sound)
            try:
                _run_ffmpeg(cmd, seconds, lambda f: progress.set(done=round(f * 100)))
                tmp.replace(out_dir / name)
            except RenderFailed as e:
                raise jobs.JobFailed("render_failed") from e
            finally:
                tmp.unlink(missing_ok=True)
        meta = {"duration": seconds, "width": size[0], "height": size[1], "fps": tl["fps"], "revision": tl["revision"],
                "clips": len(timeline.all_clips(tl)), "missing": render_args.missing_count(segs) + lost,
                "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
        write_json(out_dir / f"{name}.json", meta)
        progress.set(done=100)
        prune(pid)
        return {"rel": f"{RENDER_DIR}/{name}", **meta}

    return jobs.start(pid, "render", f"render:{pid}", "", work, busy_code="studio_render_running",
                      progress={"total": 100, "done": 0, "failed": 0, "current": ""})


def _list(pid: str) -> list[tuple[str, dict]]:
    d = root(pid) / "renders"
    out = []
    for p in d.glob("*.mp4") if d.is_dir() else []:
        if is_id(p.stem) and p.is_file() and not p.is_symlink():
            meta = read_json(p.with_name(p.name + ".json"), {})
            out.append((p.name, meta if isinstance(meta, dict) else {}))
    return sorted(out, key=lambda x: str(x[1].get("created_at") or ""), reverse=True)


def list_renders(pid: str) -> dict:
    base = project_root(pid)
    return {"renders": [{"rel": f"{RENDER_DIR}/{n}", "abs": str(base / RENDER_DIR / n), "name": n,
                         **{k: m.get(k) for k in ("duration", "width", "height", "created_at", "missing", "clips")}}
                        for n, m in _list(pid)]}


def prune(pid: str) -> None:
    """Nur die KEEP neuesten Filme behalten; nur eigene Dateien in studio/renders/."""
    for name, _ in _list(pid)[KEEP:]:
        d = root(pid) / "renders"
        (d / name).unlink(missing_ok=True)
        (d / f"{name}.json").unlink(missing_ok=True)
