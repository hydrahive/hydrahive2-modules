"""Planungsdaten des Studios: Drehbuch-Kopf, Szenen (mit Shots), Bausteine (Spec „Bauplan Etappe 2“)."""
from __future__ import annotations

import shutil
from datetime import datetime, timezone

from . import _clean, cast, presets
from ._store import is_id, new_id, project_root, read_json, root, safe_rel, write_json

IMAGE_EXT = {"png", "jpg", "jpeg", "webp", "gif"}


class PlanError(ValueError):
    def __init__(self, code: str, status: int = 400) -> None:
        super().__init__(code)
        self.code, self.status = code, status


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---- Bausteine ----------------------------------------------------------------

def list_elements(pid: str) -> list[dict]:
    d = root(pid) / "elements"
    out = []
    for child in sorted(d.iterdir()) if d.is_dir() else []:
        data = read_json(child / "element.json", None)
        if is_id(child.name) and isinstance(data, dict) and data.get("kind") in _clean.ELEMENT_KINDS:
            out.append({**data, "id": child.name})
    return out


def _element_ids(pid: str) -> set[str]:
    return {e["id"] for e in list_elements(pid)}


def save_element(pid: str, data: dict, el_id: str | None = None) -> dict:
    if el_id is not None and (not is_id(el_id) or not (root(pid) / "elements" / el_id / "element.json").is_file()):
        raise PlanError("studio_not_found", 404)
    if data.get("kind") not in _clean.ELEMENT_KINDS or not _clean.text(data.get("name"), 200):
        raise PlanError("studio_element_invalid")
    refs = [r for r in (safe_rel(pid, x, IMAGE_EXT) for x in (data.get("references") or [])) if r]
    el = _clean.element(el_id or new_id(), data, list(dict.fromkeys(refs)))
    write_json(root(pid, create=True) / "elements" / el["id"] / "element.json", el)
    return el


def delete_element(pid: str, el_id: str) -> None:
    d = root(pid) / "elements" / el_id
    if not is_id(el_id) or not d.is_dir():
        raise PlanError("studio_not_found", 404)
    shutil.rmtree(d)                                        # nur element.json – Referenzbilder liegen woanders
    remaining = _element_ids(pid)
    for sc in list_scenes(pid):                             # Verweise aus den Szenen entfernen
        write_json(_scene_path(pid, sc["id"]), _clean.scene(sc["id"], sc, remaining))


# ---- Kopf und Szenen -------------------------------------------------------------

def _scene_path(pid: str, scene_id: str):
    return root(pid) / "scenes" / f"{scene_id}.json"


def get_head(pid: str) -> dict:
    raw = read_json(root(pid) / "screenplay.json", {})
    raw = raw if isinstance(raw, dict) else {}
    order = [s for s in (raw.get("scene_order") or []) if is_id(s)]
    return {**_clean.head(raw, scene_order=order), "created_at": raw.get("created_at"), "updated_at": raw.get("updated_at")}


def save_head(pid: str, data: dict, *, scene_order: list[str] | None = None) -> dict:
    current = get_head(pid)
    existing = {s["id"] for s in list_scenes(pid)}
    order = [s for s in (scene_order if scene_order is not None else current["scene_order"]) if s in existing]
    out = {**_clean.head({**current, **data}, scene_order=list(dict.fromkeys(order))),
           "created_at": current.get("created_at") or _now(), "updated_at": _now()}
    write_json(root(pid, create=True) / "screenplay.json", out)
    return out


def list_scenes(pid: str) -> list[dict]:
    d = root(pid) / "scenes"
    by_id = {}
    elements = _element_ids(pid) if d.is_dir() else set()
    for f in sorted(d.glob("*.json")) if d.is_dir() else []:
        data = read_json(f, None)
        if is_id(f.stem) and isinstance(data, dict):
            # Beim Lesen dieselbe Prüfung wie beim Schreiben: ältere Dateien (z. B. Shots ohne `variants`) kommen
            # vollständig an, die Oberfläche bekommt nie halbe Datensätze.
            by_id[f.stem] = _clean.scene(f.stem, data, elements)
    order = [s for s in get_head(pid)["scene_order"] if s in by_id]
    return [by_id[s] for s in order] + [v for k, v in by_id.items() if k not in order]


def save_scene(pid: str, data: dict, scene_id: str | None = None) -> dict:
    if scene_id is not None and (not is_id(scene_id) or not _scene_path(pid, scene_id).is_file()):
        raise PlanError("studio_not_found", 404)
    sid = scene_id or new_id()
    old = read_json(_scene_path(pid, sid), {}) if scene_id else {}
    sc = _clean.scene(sid, {**(old if isinstance(old, dict) else {}), **data}, _element_ids(pid))
    write_json(root(pid, create=True) / "scenes" / f"{sid}.json", sc)
    if scene_id is None:
        save_head(pid, {}, scene_order=get_head(pid)["scene_order"] + [sid])
    return sc


def delete_scene(pid: str, scene_id: str) -> None:
    if not is_id(scene_id) or not _scene_path(pid, scene_id).is_file():
        raise PlanError("studio_not_found", 404)
    _scene_path(pid, scene_id).unlink()
    save_head(pid, {}, scene_order=[s for s in get_head(pid)["scene_order"] if s != scene_id])


def reorder(pid: str, order: list) -> dict:
    return save_head(pid, {}, scene_order=[s for s in order if is_id(s)])


def get_plan(pid: str) -> dict:
    # base = Projektordner, damit das Frontend Bilder über /api/files zeigen kann (wie `abs` in der Bibliothek)
    # cast je Shot (C2): wer ist im Bild – angehakt oder im Text genannt; nur zur Anzeige, wird nicht gespeichert
    elements = list_elements(pid)
    scenes = [{**sc, "shots": [{**s, "cast": cast.of_shot(sc, s, elements)} for s in sc["shots"]]} for sc in list_scenes(pid)]
    return {"base": str(project_root(pid)), "screenplay": get_head(pid), "scenes": scenes,
            "elements": elements, "presets": presets.catalog()}


def has_plan(pid: str) -> bool:
    r = root(pid)
    return (r / "screenplay.json").is_file() or any((r / "scenes").glob("*.json")) or any((r / "elements").glob("*/element.json"))
