"""Video für einen Shot erzeugen (Spec „Bauplan Etappe 3“, 3b): Image-to-Video aus dem gewählten Bild.

Höchstens 2 Videos je Server gleichzeitig (Semaphor); weitere Aufträge warten als „queued“ im eigenen Thread.
Der Shot zeigt währenddessen `video_processing`, danach `done` oder `failed`. Das Bild bleibt immer erhalten.
"""
from __future__ import annotations

import base64
import threading
from datetime import datetime, timezone

from . import generate, jobs, plan, shots, video_provider
from ._store import new_id, project_lock, project_root, root, safe_rel, write_json

MEDIA_DIR = "studio/media/videos"
MAX_PARALLEL = 2
_slots = threading.BoundedSemaphore(MAX_PARALLEL)
_MIME = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp", "gif": "image/gif"}


def _set_shot(pid: str, scene_id: str, shot_id: str, **fields) -> None:
    with project_lock(pid):                               # Lesen-Ändern-Schreiben ohne fremde Änderung dazwischen
        scene = shots.load_scene(pid, scene_id)
        items = list(scene.get("shots") or [])
        for i, s in enumerate(items):
            if isinstance(s, dict) and s.get("id") == shot_id:
                items[i] = {**s, **fields}
                shots.save_shots(pid, scene, items)
                return
    raise jobs.JobFailed("shot_gone")


def _image_data_url(pid: str, rel: str) -> str:
    if not safe_rel(pid, rel, plan.IMAGE_EXT):
        raise jobs.JobFailed("image_gone")
    ext = rel.rsplit(".", 1)[-1].lower()
    data = base64.b64encode((project_root(pid) / rel).read_bytes()).decode("ascii")
    return f"data:{_MIME.get(ext, 'image/png')};base64,{data}"


def _work(pid: str, scene_id: str, shot_id: str) -> dict:
    with _slots:
        scene = shots.load_scene(pid, scene_id)
        shot = generate._find(scene, shot_id)
        head = plan.get_head(pid)
        model = head["models"]["video"] or video_provider.server_default_model()
        duration = video_provider.nearest(int(shot.get("duration") or 5), video_provider.allowed_durations(model))
        image_rel = shot.get("image_rel") or ""
        prompt = generate.build_prompt(pid, scene, shot)
        # Hat der Shot schon ein Video, bleibt es bei einem Fehlschlag stehen: dann zurück auf „fertig“, sonst „fehlgeschlagen“
        back = "done" if shot.get("video_rel") else "failed"
        _set_shot(pid, scene_id, shot_id, status="video_processing")
        try:
            rid = video_provider.submit_video(model=model, prompt=prompt, image_url=_image_data_url(pid, image_rel),
                                              duration=duration, aspect_ratio=video_provider.fit_aspect(model, head["aspect_ratio"]))
            url = video_provider.wait_for_video(rid, duration=duration)
            name = f"{new_id()}.mp4"
            target = root(pid, create=True) / "media" / "videos" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            video_provider.download_video(url, target)
        except (video_provider.ProviderError, jobs.JobFailed) as e:
            _set_shot(pid, scene_id, shot_id, status=back)
            raise jobs.JobFailed(str(e)) from e
        rel = f"{MEDIA_DIR}/{name}"
        created = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        write_json(target.with_name(name + ".json"), {"prompt": prompt, "model": model, "duration": duration,
                                                      "source_image": image_rel, "shot_id": shot_id, "scene_id": scene_id,
                                                      "created_at": created})
        _set_shot(pid, scene_id, shot_id, status="done", video_rel=rel, still=False)    # G4: doch bewegt
        return {"video_rel": rel, "model": model, "duration": duration}


def start_video(pid: str, scene_id: str, shot_id: str) -> dict:
    shot = generate._find(shots.load_scene(pid, scene_id), shot_id)        # 404 vor dem Auftrag
    if not shot.get("image_rel"):
        raise plan.PlanError("studio_video_needs_image")
    return jobs.start(pid, "video", shot_id, scene_id, lambda: _work(pid, scene_id, shot_id))
