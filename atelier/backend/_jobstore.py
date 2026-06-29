"""Atelier — gemeinsamer dateibasierter Job-Store für Media-Jobs.

Video- und Film-Jobs liegen als ``<dir>/<job_id>.json`` im Projekt-Workspace.
Diese Helfer kapseln Lesen/Schreiben/Löschen, damit video.py und film.py keine
duplizierte Store-Logik tragen.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from . import storage


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_job(job_dir: Path, job: dict) -> None:
    (job_dir / f"{job['job_id']}.json").write_text(
        json.dumps(job, ensure_ascii=False, indent=2), "utf-8"
    )


def list_jobs(job_dir: Path) -> list[dict]:
    """Alle Jobs im Verzeichnis (neueste zuerst)."""
    jobs: list[dict] = []
    for p in job_dir.glob("*.json"):
        try:
            jobs.append(json.loads(p.read_text("utf-8")))
        except (json.JSONDecodeError, OSError):
            continue
    jobs.sort(key=lambda j: j.get("created_at") or "", reverse=True)
    return jobs


def delete_job(project_id: str, job_dir: Path, job_id: str, media_key: str) -> bool:
    """Löscht Job-JSON + zugehörige Mediendatei (media_key = video_rel/film_rel).

    True bei Erfolg, False wenn ID ungültig oder Job nicht vorhanden.
    """
    if not storage.is_valid_id(job_id):
        return False
    jp = job_dir / f"{job_id}.json"
    if not jp.is_file():
        return False
    try:
        job = json.loads(jp.read_text("utf-8"))
        rel = job.get(media_key)
        if rel:
            media = storage.safe_under(storage.atelier_root(project_id), rel)
            if media is not None:
                media.unlink(missing_ok=True)
    except (json.JSONDecodeError, OSError):
        pass
    jp.unlink(missing_ok=True)
    return True
