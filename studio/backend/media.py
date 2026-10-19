"""Medien des Studios löschen und ihre Verwendung zeigen (Spec „C1 im Detail“).

Gelöscht werden darf nur, was das Studio selbst ablegt (OWN_DIRS); Atelier, Video-Editor und Tonstudio bleiben
unangetastet. Nach dem Löschen werden Shots (Varianten, Bild, Video, Sprache) und Bausteine (Referenzen) bereinigt.
Clips der Zeitleiste bleiben stehen und werden beim Laden zu Platzhaltern bzw. stummen Tonclips.
"""
from __future__ import annotations

from pathlib import Path

from . import jobs, plan, shots, timeline
from ._sources import AUDIO_EXT, IMAGE_EXT, VIDEO_EXT
from ._store import project_lock, project_root, read_json, write_json

OWN_DIRS = ("studio/media/images/", "studio/media/videos/", "studio/media/voice/", "studio/media/music/",
            "studio/media/free/", "studio/media/uploads/", "studio/renders/", "studio/media/probes/")
EXTS = IMAGE_EXT | VIDEO_EXT | AUDIO_EXT


def is_own(rel) -> bool:
    """Liegt `rel` direkt (ohne Unterordner, ohne ..) in einem Ordner des Studios und hat eine Medien-Endung?"""
    if not isinstance(rel, str) or "\\" in rel or "\0" in rel:
        return False
    for d in OWN_DIRS:
        name = rel[len(d):] if rel.startswith(d) else ""
        if name and "/" not in name and not name.startswith(".") and name.rsplit(".", 1)[-1].lower() in EXTS:
            return True
    return False


def _file(pid: str, rel: str) -> Path:
    if not is_own(rel):
        raise plan.PlanError("studio_media_not_own", 403)
    base = project_root(pid)
    p = base / rel
    if p.is_symlink() or not p.is_file() or not p.resolve().is_relative_to(base.resolve()):
        raise plan.PlanError("studio_media_not_found", 404)
    return p


def _shot_uses(s: dict, rel: str) -> bool:
    return rel in (s.get("image_rel"), s.get("video_rel"), s.get("voice_rel")) or rel in (s.get("variants") or [])


def usage(pid: str, rel) -> dict:
    """Wo wird die Datei benutzt? Shots (mit Namen), Zahl der Clips, Bausteine."""
    used_shots = []
    for sc in plan.list_scenes(pid):
        for i, s in enumerate(sc.get("shots") or []):
            if isinstance(s, dict) and isinstance(rel, str) and _shot_uses(s, rel):
                used_shots.append({"scene_id": sc["id"], "shot_id": s.get("id"), "label": f"{sc.get('title') or ''} · Shot {i + 1}"})
    clips = sum(1 for c in timeline.all_clips(timeline.load(pid)) if c.get("media_rel") == rel) if isinstance(rel, str) else 0
    elements = [{"id": e["id"], "name": e.get("name") or ""} for e in plan.list_elements(pid)
                if rel in (e.get("references") or []) or (isinstance(rel, str) and rel and e.get("probe_rel") == rel)]
    return {"own": is_own(rel), "shots": used_shots, "clips": clips, "elements": elements}


def _clean_shot(s: dict, rel: str) -> dict:
    variants = [v for v in s.get("variants") or [] if v != rel]
    image = s.get("image_rel")
    if image == rel:
        image = variants[-1] if variants else None
    out = {**s, "variants": variants, "image_rel": image}
    for key in ("video_rel", "voice_rel"):
        if out.get(key) == rel:
            out[key] = None
    if not image and not out.get("video_rel"):
        out["status"] = "planned"
    return out


def delete(pid: str, rel) -> dict:
    p = _file(pid, rel)
    with project_lock(pid):
        scenes = plan.list_scenes(pid)
        hit = [(sc, s) for sc in scenes for s in sc.get("shots") or [] if isinstance(s, dict) and _shot_uses(s, rel)]
        if any((pid, s.get("id")) in jobs._running for _, s in hit):
            raise plan.PlanError("studio_media_busy", 409)
        p.unlink()
        p.with_name(p.name + ".json").unlink(missing_ok=True)
        for scene_id in dict.fromkeys(sc["id"] for sc, _ in hit):
            raw = shots.load_scene(pid, scene_id)
            shots.save_shots(pid, raw, [_clean_shot(s, rel) if isinstance(s, dict) and _shot_uses(s, rel) else s
                                        for s in raw.get("shots") or []])
        for e in plan.list_elements(pid):
            if rel in (e.get("references") or []) or e.get("probe_rel") == rel:
                path = plan.root(pid) / "elements" / e["id"] / "element.json"
                data = read_json(path, {})
                out = {**data, "references": [r for r in data.get("references") or [] if r != rel]}
                if data.get("probe_rel") == rel:                         # G2: Probebild weg → Freigabe weg
                    out.update(probe_rel="", approved=False)
                write_json(path, out)
    return {"deleted": rel}
