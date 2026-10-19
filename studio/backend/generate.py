"""Bild für einen Shot erzeugen (Spec „Bauplan Etappe 3“, 3a).

Prompt-Aufbau nach dem Vorbild atelier/backend/generate.build_prompt: zuerst der feste Look, dann die Bausteine wörtlich,
dann der Shot, zuletzt Kamera und Licht. So bleibt das Gleichbleibende vorn und die Regie verändert nur.
"""
from __future__ import annotations

from datetime import datetime, timezone

from . import _clean, _image_request, image_provider, jobs, plan, shots
from ._store import new_id, project_lock, root, safe_rel, write_json

MAX_VARIANTS = 8
MEDIA_DIR = "studio/media/images"


# Auftrag, Vorlagen und Startwert: _image_request (Bauplan H). Die Namen bleiben hier für bestehende Aufrufer.
build_prompt = _image_request.build_prompt
reference_urls = _image_request.reference_urls
_cast = _image_request.cast_of


def _find(scene: dict, shot_id: str) -> dict:
    for s in scene.get("shots") or []:
        if isinstance(s, dict) and s.get("id") == shot_id:
            return s
    raise plan.PlanError("studio_not_found", 404)


def _work(pid: str, scene_id: str, shot_id: str, *, change: str = "", fresh: bool = False) -> dict:
    scene = shots.load_scene(pid, scene_id)
    shot = _find(scene, shot_id)
    head = plan.get_head(pid)
    model = head["models"]["image"] or image_provider.server_default_model()
    base = shot.get("image_rel") or "" if change else ""
    if change and not safe_rel(pid, base, plan.IMAGE_EXT):
        raise jobs.JobFailed("image_gone")
    prompt = _image_request.build_prompt(pid, scene, shot, change)
    seed = _image_request.seed_of(pid, scene, shot, fresh=fresh)
    try:
        raw = image_provider.request_image(model=model, prompt=prompt, aspect_ratio=head["aspect_ratio"], seed=seed,
                                           references=_image_request.reference_urls(pid, shot, scene, base_image=base))
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
    write_json(target.with_name(target.name + ".json"), {"prompt": prompt, "model": model, "shot_id": shot_id, "seed": seed,
                                                         "scene_id": scene_id, "created_at": created,
                                                         **({"change": change, "from": base} if change else {})})
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


def start_image(pid: str, scene_id: str, shot_id: str, data: dict | None = None) -> dict:
    """`fresh`: anderes Bild mit neuem Startwert (H4). `change`: gezeigtes Bild gezielt ändern (H6)."""
    data = data if isinstance(data, dict) else {}
    shot = _find(shots.load_scene(pid, scene_id), shot_id)       # 404 vor dem Auftrag
    change = ""
    if "change" in data:
        if not shot.get("image_rel"):
            raise plan.PlanError("studio_change_needs_image")
        change = _image_request.check_change(data["change"])
    fresh = data.get("fresh") is True
    return jobs.start(pid, "image", shot_id, scene_id, lambda: _work(pid, scene_id, shot_id, change=change, fresh=fresh))


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
