"""Sprache je Shot (Spec „Bauplan 5c“, 5c-1): Sprechtext → Tondatei unter studio/media/voice/, `voice_rel` am Shot.

Eine Datei wird erst angenommen, wenn ffprobe sie als Ton erkennt. Die alte Sprache bleibt als Datei erhalten
(Bibliothek), der Shot zeigt auf die neue. Höchstens zwei Sprachaufträge laufen gleichzeitig (wie Videos).
"""
from __future__ import annotations

import json
import subprocess
import threading
from datetime import datetime, timezone

from . import generate, jobs, plan, shots, voice_provider
from ._store import new_id, project_lock, root, write_json

MEDIA_DIR = "studio/media/voice"
_slots = threading.BoundedSemaphore(2)


def probe_seconds(path) -> float | None:
    """Länge in Sekunden, wenn ffprobe die Datei als Ton erkennt, sonst None."""
    try:
        out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "format=duration:stream=codec_type",
                              "-of", "json", str(path)], capture_output=True, text=True, timeout=30, check=False)
        data = json.loads(out.stdout or "{}")
        if not data.get("streams"):
            return None
        d = float(data.get("format", {}).get("duration") or 0)
        return round(d, 3) if d > 0 else None
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def _set_voice(pid: str, scene_id: str, shot_id: str, rel: str) -> None:
    with project_lock(pid):
        scene = shots.load_scene(pid, scene_id)
        items = list(scene.get("shots") or [])
        for i, s in enumerate(items):
            if isinstance(s, dict) and s.get("id") == shot_id:
                items[i] = {**s, "voice_rel": rel}
                shots.save_shots(pid, scene, items)
                return
    raise jobs.JobFailed("shot_gone")


def work(pid: str, scene_id: str, shot_id: str) -> dict:
    with _slots:
        shot = generate._find(shots.load_scene(pid, scene_id), shot_id)
        text = (shot.get("speech") or "").strip()
        if not text:
            raise jobs.JobFailed("no_text")
        model = plan.get_head(pid)["models"]["voice"] or voice_provider.server_default_model()
        try:
            data, ext, used, note = voice_provider.synthesize(text, shot.get("voice") or "", model)
        except voice_provider.ProviderError as e:
            raise jobs.JobFailed(str(e)) from e
        name = f"{new_id()}.{ext if ext in ('wav', 'mp3') else 'wav'}"
        target = root(pid, create=True) / "media" / "voice" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        seconds = probe_seconds(target)
        if seconds is None:
            target.unlink(missing_ok=True)
            raise jobs.JobFailed("bad_audio")
        meta = {"text": text, "voice": used, "model": model, "duration": seconds, "shot_id": shot_id, "scene_id": scene_id,
                "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), **({"note": note} if note else {})}
        write_json(target.with_name(name + ".json"), meta)
        rel = f"{MEDIA_DIR}/{name}"
        _set_voice(pid, scene_id, shot_id, rel)
        return {"voice_rel": rel, "duration": seconds, "model": model, "voice": used}


def start(pid: str, scene_id: str, shot_id: str) -> dict:
    shot = generate._find(shots.load_scene(pid, scene_id), shot_id)          # 404 vor dem Auftrag
    if not (shot.get("speech") or "").strip():
        raise plan.PlanError("studio_speech_needs_text")
    return jobs.start(pid, "speech", shot_id, scene_id, lambda: work(pid, scene_id, shot_id))
