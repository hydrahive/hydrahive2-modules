"""Shots einer Szene bearbeiten (Spec „Bauplan 2b“). Shots liegen in scenes/<id>.json → shots[]."""
from __future__ import annotations

from . import _clean, plan
from ._store import is_id, project_lock, read_json, write_json

MAX_SHOTS = 50
EDITABLE = ("shot", "prompt", "element_ids", "excluded_ids", "duration", "speech", "voice")      # Status und Medien ändert nur das Erzeugen (Etappe 3)


def load_scene(pid: str, scene_id: str) -> dict:
    path = plan._scene_path(pid, scene_id) if is_id(scene_id) else None
    data = read_json(path, None) if path is not None and path.is_file() else None
    if not isinstance(data, dict):
        raise plan.PlanError("studio_not_found", 404)
    return {**data, "id": scene_id}


def scene_elements(pid: str, scene: dict) -> set[str]:
    """Bausteine, die ein Shot nutzen darf: jeder vorhandene (C2 – früher nur die der Szene, das verschluckte Häkchen)."""
    return plan._element_ids(pid)


def save_shots(pid: str, scene: dict, shots: list[dict]) -> list[dict]:
    allowed = scene_elements(pid, scene)
    clean = [_clean.shot(s, i, allowed) for i, s in enumerate(shots)][:MAX_SHOTS]
    write_json(plan._scene_path(pid, scene["id"]), {**scene, "shots": clean})
    return clean


def _find(scene: dict, shot_id: str) -> int:
    for i, s in enumerate(scene.get("shots") or []):
        if isinstance(s, dict) and s.get("id") == shot_id and is_id(shot_id):
            return i
    raise plan.PlanError("studio_not_found", 404)


def _editable(data: dict) -> dict:
    return {k: data[k] for k in EDITABLE if k in data}


def _locked(fn):
    """Lesen-Ändern-Schreiben einer Szene unter der Projektsperre (Aufträge schreiben gleichzeitig in die Szene)."""
    def run(pid: str, *args, **kw):
        with project_lock(pid):
            return fn(pid, *args, **kw)
    run.__name__, run.__doc__ = fn.__name__, fn.__doc__
    return run


@_locked
def add(pid: str, scene_id: str, data: dict) -> dict:
    scene = load_scene(pid, scene_id)
    shots = list(scene.get("shots") or [])
    if len(shots) >= MAX_SHOTS:
        raise plan.PlanError("studio_too_many_shots")
    new = {"duration": plan.get_head(pid)["default_duration"], **_editable(data), "status": "planned"}
    return save_shots(pid, scene, [*shots, new])[-1]


@_locked
def update(pid: str, scene_id: str, shot_id: str, data: dict) -> dict:
    scene = load_scene(pid, scene_id)
    shots = list(scene.get("shots") or [])
    i = _find(scene, shot_id)
    shots[i] = {**shots[i], **_editable(data), "id": shot_id}
    return save_shots(pid, scene, shots)[i]


@_locked
def delete(pid: str, scene_id: str, shot_id: str) -> None:
    scene = load_scene(pid, scene_id)
    i = _find(scene, shot_id)
    save_shots(pid, scene, [s for j, s in enumerate(scene.get("shots") or []) if j != i])


@_locked
def reorder(pid: str, scene_id: str, shot_ids: list) -> list[dict]:
    scene = load_scene(pid, scene_id)
    by_id = {s.get("id"): s for s in scene.get("shots") or [] if isinstance(s, dict)}
    wanted = [i for i in dict.fromkeys(x for x in shot_ids if isinstance(x, str)) if i in by_id]
    rest = [i for i in by_id if i not in wanted]
    return save_shots(pid, scene, [by_id[i] for i in wanted + rest])
