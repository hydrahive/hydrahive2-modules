"""Übersicht eines Projekts für Start-Reiter und Fortschritt (Spec „Etappe B“, B1). Nur lesend, legt nichts an."""
from __future__ import annotations

from . import draft_book, import_atelier, plan, timeline


def overview(pid: str) -> dict:
    scenes = plan.list_scenes(pid)
    shots = [s for sc in scenes for s in sc.get("shots") or []]
    atelier = import_atelier.preview(pid)
    return {
        "scenes": len(scenes),
        "shots": len(shots),
        "with_image": sum(1 for s in shots if s.get("image_rel")),
        "with_video": sum(1 for s in shots if s.get("video_rel")),
        "clips": len(timeline.all_clips(timeline.load(pid))),
        "atelier": bool(atelier["available"]) and not atelier["plan_exists"],
        "books": draft_book.count(pid),
    }
