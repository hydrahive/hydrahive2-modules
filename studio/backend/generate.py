"""Bild für einen Shot erzeugen (Spec „Bauplan Etappe 3“, 3a).

Prompt-Aufbau nach dem Vorbild atelier/backend/generate.build_prompt: zuerst der feste Look, dann die Bausteine wörtlich,
dann der Shot, zuletzt Kamera und Licht. So bleibt das Gleichbleibende vorn und die Regie verändert nur.
"""
from __future__ import annotations

import base64
from datetime import datetime, timezone

from . import _clean, cast, image_provider, jobs, plan, presets, shots
from ._clean import CAMERA_KEYS
from ._store import new_id, project_lock, project_root, root, safe_rel, write_json

MAX_REFERENCES = 3           # mehr nehmen manche Modelle nicht an (HTTP 400)
MAX_VARIANTS = 8
MEDIA_DIR = "studio/media/images"
_MIME = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp", "gif": "image/gif"}


def _cast(pid: str, scene: dict, shot: dict) -> list[dict]:
    """Bausteine im Bild: angehakt oder im Text genannt (C2), in dieser Reihenfolge."""
    els = plan.list_elements(pid)
    by_id = {e["id"]: e for e in els}
    return [by_id[i] for i in cast.of_shot(scene, shot, els)]


def build_prompt(pid: str, scene: dict, shot: dict) -> str:
    head = plan.get_head(pid)
    parts: list[str] = []
    if head["look"]["style"]:
        parts.append(head["look"]["style"])
    cast_ = _cast(pid, scene, shot)
    palette = list(head["look"]["palette"])
    for e in cast_:
        desc = e.get("description") or ""
        parts.append(f"{e['name']}: {desc}" if desc else e["name"])
        if e.get("style_anchor"):
            parts.append(e["style_anchor"])
        palette += [c for c in e.get("palette") or [] if c not in palette]
    if palette:
        parts.append("color palette: " + ", ".join(palette[:12]))
    if shot.get("prompt"):
        parts.append(shot["prompt"])
    if shot.get("shot"):
        parts.append(presets.phrase_for("shot", shot["shot"]) or "")
    cam = scene.get("camera") or {}
    parts += [presets.phrase_for(k, cam[k]) or "" for k in CAMERA_KEYS if k != "shot" and cam.get(k)]
    # Teile enden oft schon mit einem Satzzeichen (z. B. Beschreibungen aus der KI) – nicht doppelt setzen.
    return ". ".join(t for t in (p.strip().rstrip(".").strip() for p in parts) if t)


def reference_urls(pid: str, shot: dict, scene: dict | None = None) -> list[str]:
    """Vorlage-Fotos der Bausteine im Bild als data:-URLs (nur echte Bilder im Projekt, höchstens 3)."""
    urls: list[str] = []
    for e in _cast(pid, scene or {}, shot):
        for rel in e.get("references") or []:
            if not safe_rel(pid, rel, plan.IMAGE_EXT):
                continue
            ext = rel.rsplit(".", 1)[-1].lower()
            data = base64.b64encode((project_root(pid) / rel).read_bytes()).decode("ascii")
            urls.append(f"data:{_MIME.get(ext, 'image/png')};base64,{data}")
            if len(urls) >= MAX_REFERENCES:
                return urls
    return urls


def _find(scene: dict, shot_id: str) -> dict:
    for s in scene.get("shots") or []:
        if isinstance(s, dict) and s.get("id") == shot_id:
            return s
    raise plan.PlanError("studio_not_found", 404)


def _work(pid: str, scene_id: str, shot_id: str) -> dict:
    scene = shots.load_scene(pid, scene_id)
    shot = _find(scene, shot_id)
    head = plan.get_head(pid)
    model = head["models"]["image"] or image_provider.server_default_model()
    prompt = build_prompt(pid, scene, shot)
    try:
        raw = image_provider.request_image(model=model, prompt=prompt, references=reference_urls(pid, shot, scene),
                                           aspect_ratio=head["aspect_ratio"])
    except image_provider.ProviderError as e:
        raise jobs.JobFailed(str(e)) from e
    ext = image_provider.image_kind(raw)
    if ext is None:
        raise jobs.JobFailed("bad_image")
    rel = f"{MEDIA_DIR}/{new_id()}.{ext}"
    target = root(pid, create=True) / "media" / "images" / rel.rsplit("/", 1)[-1]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    created = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    write_json(target.with_name(target.name + ".json"), {"prompt": prompt, "model": model, "shot_id": shot_id,
                                                         "scene_id": scene_id, "created_at": created})
    _attach(pid, scene_id, shot_id, rel)
    return {"image_rel": rel, "model": model}


def _attach(pid: str, scene_id: str, shot_id: str, rel: str) -> None:
    """Neues Bild an den Shot hängen (Szene frisch laden – der Nutzer kann inzwischen bearbeitet haben)."""
    with project_lock(pid):
        scene = shots.load_scene(pid, scene_id)
        items = list(scene.get("shots") or [])
        for i, s in enumerate(items):
            if isinstance(s, dict) and s.get("id") == shot_id:
                variants = [v for v in s.get("variants") or [] if isinstance(v, str) and v != rel] + [rel]
                items[i] = {**s, "image_rel": rel, "variants": variants[-MAX_VARIANTS:],
                            "status": "image_ready" if s.get("status") in (None, "planned", "failed", "image_ready") else s["status"]}
                shots.save_shots(pid, scene, items)
                return
    raise jobs.JobFailed("shot_gone")


def start_image(pid: str, scene_id: str, shot_id: str) -> dict:
    _find(shots.load_scene(pid, scene_id), shot_id)       # 404 vor dem Auftrag
    return jobs.start(pid, "image", shot_id, scene_id, lambda: _work(pid, scene_id, shot_id))


def assign(pid: str, scene_id: str, shot_id: str, rel) -> dict:
    """Ein Bild des Studios (frei oder je Shot erzeugt) als aktuelles Bild und Variante des Shots (B3)."""
    _find(shots.load_scene(pid, scene_id), shot_id)       # 404 vor der Pfadprüfung
    ok = isinstance(rel, str) and rel.startswith(_clean.VARIANT_DIRS) and ".." not in rel and safe_rel(pid, rel, plan.IMAGE_EXT)
    if not ok:
        raise plan.PlanError("studio_assign_invalid")
    _attach(pid, scene_id, shot_id, rel)
    return _find(shots.load_scene(pid, scene_id), shot_id)


def choose_variant(pid: str, scene_id: str, shot_id: str, rel) -> dict:
    with project_lock(pid):
        return _choose(pid, scene_id, shot_id, rel)


def _choose(pid: str, scene_id: str, shot_id: str, rel) -> dict:
    scene = shots.load_scene(pid, scene_id)
    items = list(scene.get("shots") or [])
    for i, s in enumerate(items):
        if isinstance(s, dict) and s.get("id") == shot_id:
            if not isinstance(rel, str) or rel not in (s.get("variants") or []):
                raise plan.PlanError("studio_variant_unknown")
            items[i] = {**s, "image_rel": rel}
            return shots.save_shots(pid, scene, items)[i]
    raise plan.PlanError("studio_not_found", 404)
