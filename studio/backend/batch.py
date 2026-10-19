"""Sammelaufträge (Spec „Bauplan 3c“): alle Szenen zerlegen, Bilder für alle Shots, Videos für alle Shots.

Je Projekt höchstens einer. Die Schritte laufen nacheinander im Auftrags-Thread und nutzen dieselben Bausteine wie die
Einzelaufträge (generate._work, generate_video._work, director.decompose). Fertiges wird übersprungen; ein Fehler bei
einem Schritt zählt als fehlgeschlagen, der Rest läuft weiter. Abbrechen greift nach dem laufenden Schritt.
"""
from __future__ import annotations

import asyncio
import logging

from . import (
    director,
    generate,
    generate_video,
    image_provider,
    jobs,
    plan,
    speech,
    video_provider,
    voice_provider,
)

logger = logging.getLogger("hhmod_studio.batch")

KINDS = ("decompose_all", "images_all", "videos_all", "speech_all")


def _steps(pid: str, kind: str) -> list[tuple[str, str | None, str]]:
    """(Szene, Shot oder None, Anzeigename) – nur was noch fehlt, in Drehbuch-Reihenfolge."""
    out = []
    for n, scene in enumerate(plan.list_scenes(pid), start=1):
        title = scene.get("title") or f"#{n}"
        shots = [s for s in scene.get("shots") or [] if isinstance(s, dict)]
        if kind == "decompose_all":
            if not shots:
                out.append((scene["id"], None, title))
            continue
        for i, s in enumerate(shots, start=1):
            if kind == "speech_all":
                want = bool((s.get("speech") or "").strip()) and not s.get("voice_rel")
            elif kind == "images_all":
                want = not s.get("image_rel")
            else:
                want = bool(s.get("image_rel")) and not s.get("video_rel")
            if want:
                out.append((scene["id"], s["id"], f"{title} · Shot {i}"))
    return out


def _model(pid: str, kind: str) -> str:
    models = plan.get_head(pid)["models"]
    if kind == "decompose_all":
        from hydrahive.llm.client import default_model
        return models["text"] or default_model()
    if kind == "images_all":
        return models["image"] or image_provider.server_default_model()
    if kind == "speech_all":
        return models["voice"] or voice_provider.server_default_model()
    return models["video"] or video_provider.server_default_model()


def preview(pid: str, kind: str) -> dict:
    if kind not in KINDS:
        raise plan.PlanError("studio_not_found", 404)
    return {"count": len(_steps(pid, kind)), "model": _model(pid, kind)}


def _run_step(pid: str, kind: str, scene_id: str, shot_id: str | None) -> None:
    if kind == "decompose_all":
        asyncio.run(director.decompose(pid, scene_id))
    elif kind == "images_all":
        generate._work(pid, scene_id, shot_id)
    elif kind == "speech_all":
        speech.work(pid, scene_id, shot_id)
    else:
        generate_video._work(pid, scene_id, shot_id)


def start(pid: str, kind: str) -> dict:
    if kind not in KINDS:
        raise plan.PlanError("studio_not_found", 404)
    steps = _steps(pid, kind)
    if not steps:
        raise plan.PlanError("studio_batch_nothing")

    def work(progress: jobs.Progress) -> dict:
        done = failed = 0
        for scene_id, shot_id, name in steps:
            if progress.cancelled():
                raise jobs.Cancelled()
            progress.set(current=name, current_shot=shot_id or "")
            try:
                _run_step(pid, kind, scene_id, shot_id)
                done += 1
            except (jobs.JobFailed, plan.PlanError) as e:
                logger.info("Studio-Sammelauftrag %s: Schritt %s fehlgeschlagen (%s)", kind, name, e)
                failed += 1
            progress.set(done=done, failed=failed)
        progress.set(current="", current_shot="")
        return {"done": done, "failed": failed}

    return jobs.start(pid, kind, f"batch:{pid}", "", work, busy_code="studio_batch_running",
                      progress={"total": len(steps), "done": 0, "failed": 0, "current": "", "current_shot": ""})
