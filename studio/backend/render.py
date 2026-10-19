"""Film als MP4 rendern (Spec „Bauplan 4d“, 7b, 7c): Auftrag in der Warteschlange, Fortschritt, Ablage studio/renders/.

Die Schnittfassung wird beim Klick gelesen (Revision in der Begleitdatei) – ein wartender Film nimmt den Schnitt von
damals. ffmpeg läuft als Kindprozess mit Zeitgrenze; der Fortschritt kommt aus `-progress pipe:1` (out_time_us).
Abbrechen (auch des laufenden Films) beendet ffmpeg. Liste und Aufräumen: render_store.py.
"""
from __future__ import annotations

import logging
import tempfile
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

from . import (
    jobs,
    mix,
    plan,
    render_args,
    render_ffmpeg,
    render_preset,
    render_queue,
    render_store,
    subtitle_format,
    subtitles,
    timeline,
)
from ._sources import AUDIO_EXT, IMAGE_EXT, VIDEO_EXT
from ._store import new_id, project_root, root, safe_rel, write_json

logger = logging.getLogger("hhmod_studio.render")

RENDER_DIR = render_store.RENDER_DIR
list_renders, prune = render_store.list_renders, render_store.prune


RenderFailed = render_ffmpeg.RenderFailed
_has_audio = render_ffmpeg.has_audio


def _run_ffmpeg(cmd: list[str], seconds: float, progress: Callable[[float], None], stop: Callable[[], bool] | None = None) -> None:
    """Über diesen Namen, damit Tests ffmpeg ersetzen können (auch subtitle_hear benutzt ihn)."""
    render_ffmpeg.run(cmd, seconds, progress, stop)


def _segments(pid: str, clips: list[dict]) -> list[dict]:
    def exists(rel: str) -> bool:
        return bool(safe_rel(pid, rel, IMAGE_EXT | VIDEO_EXT))
    segs = render_args.segments(clips, exists=exists)
    for s in segs:
        if s["kind"] == "video":
            s["has_audio"] = _has_audio(project_root(pid) / s["media"])
    return segs


def _audio(pid: str, tl: dict) -> list[dict]:
    sound = [{**c, "track": t["id"]} for t in tl["tracks"] if t["kind"] == "audio" for c in t["clips"]]
    return render_args.audio_parts(sound, exists=lambda rel: bool(safe_rel(pid, rel, AUDIO_EXT)))


def _subtitle_files(pid: str, td: Path) -> list[dict]:
    """Alle Sprachen mit Untertiteln als SRT im Arbeitsordner (Filmsprache zuerst)."""
    out = []
    for entry in subtitles.languages(pid)["languages"]:
        cues = subtitles.load(pid, entry["language"])["cues"]
        if cues:
            f = td / f"{entry['language']}.srt"
            f.write_text(subtitle_format.srt(cues), encoding="utf-8")
            out.append({"file": f, "language": entry["language"]})
    return out


def start(pid: str, *, with_subtitles: bool = False, aspect=None, quality=None) -> dict:
    """`aspect`/`quality`: Vorlage (7b); None = Format des Drehbuchs bzw. Standard. Unbekannt → studio_render_bad_preset."""
    head = plan.get_head(pid)
    try:
        preset = render_preset.resolve(aspect, quality, head["aspect_ratio"])
    except ValueError as e:
        raise plan.PlanError("studio_render_bad_preset") from e
    tl = timeline.load(pid)
    clips = timeline.clips_of(tl)
    if not clips and not _audio(pid, tl):          # nur gelöschter Ton ergäbe einen Film der Länge 0
        raise plan.PlanError("studio_render_empty")
    try:
        ticket, position = render_queue.enter(pid)
    except render_queue.QueueFull as e:
        raise plan.PlanError("studio_render_queue_full", 409) from e

    def work(progress: jobs.Progress) -> dict:
        with render_queue.turn(ticket, progress):
            return _render(pid, tl, clips, head, preset, with_subtitles, progress)

    info = {"aspect": preset["aspect"], "quality": preset["quality"], "subtitles": with_subtitles}
    try:
        job = jobs.start(pid, "render", f"render:{ticket}", "", work, status="queued", info=info,
                         progress={"total": 100, "done": 0, "failed": 0, "current": ""})
    except BaseException:
        render_queue.leave(ticket)
        raise
    return {**job, "position": position}


def _render(pid: str, tl: dict, clips: list[dict], head: dict, preset: dict, with_subtitles: bool,
            progress: jobs.Progress) -> dict:
    """Den Film rendern (läuft, wenn er in der Warteschlange dran ist). Abbrechen beendet ffmpeg."""
    size = preset["size"]

    def step(f: float) -> None:
        if progress.cancelled():
            raise jobs.Cancelled()
        progress.set(done=round(f * 100))

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
        subs = _subtitle_files(pid, Path(td)) if with_subtitles else []
        cmd = render_args.command(segs, project_root(pid), tmp, size=size, fps=tl["fps"], text_files=texts, audio=sound,
                                  mixer=mix.Mixer.of(tl), subtitles=subs, default_language=head["language"],
                                  crf=preset["crf"])
        try:
            _run_ffmpeg(cmd, seconds, step, stop=progress.cancelled)
            tmp.replace(out_dir / name)
        except RenderFailed as e:
            raise jobs.JobFailed("render_failed") from e
        finally:
            tmp.unlink(missing_ok=True)
    meta = {"duration": seconds, "width": size[0], "height": size[1], "aspect": preset["aspect"], "quality": preset["quality"],
            "fps": tl["fps"], "revision": tl["revision"],
            "clips": len(timeline.all_clips(tl)), "missing": render_args.missing_count(segs) + lost,
            "subtitles": [x["language"] for x in subs],
            "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    write_json(out_dir / f"{name}.json", meta)
    progress.set(done=100)
    prune(pid)
    return {"rel": f"{RENDER_DIR}/{name}", **meta}
