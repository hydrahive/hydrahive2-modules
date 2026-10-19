"""Probebild einer Figur / eines Ortes (Spec „Bauplan G2“): so sieht der Baustein im Film aus.

Ein Bild-Auftrag wie je Shot (generate.py), aber für den Baustein: Look des Drehbuchs + Name + Beschreibung, die Fotos
des Bausteins als Vorlage. Ein neues Probebild hebt die Freigabe auf; das alte bleibt in der Sammlung.
"""
from __future__ import annotations

import base64
from datetime import datetime, timezone

from . import image_provider, jobs, plan
from ._clean import PROBE_DIR
from ._store import (
    new_id,
    project_lock,
    project_root,
    read_json,
    root,
    safe_rel,
    write_json,
)

MAX_REFERENCES = 3
ASPECT = "16:9"
_MIME = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp", "gif": "image/gif"}


def _element(pid: str, el_id: str) -> dict:
    el = next((e for e in plan.list_elements(pid) if e["id"] == el_id), None)
    if el is None:
        raise plan.PlanError("studio_not_found", 404)
    return el


def build_prompt(pid: str, el: dict) -> str:
    look = plan.get_head(pid)["look"]["style"]
    who = f"{el['name']}: {el['description']}" if el.get("description") else el["name"]
    if el["kind"] == "place":
        what = f"Establishing view of {who}. Wide shot, clear daylight, no people in front"
    elif el["kind"] == "object":
        what = f"Product view of {who}. Centered, neutral background"
    else:
        what = f"Character sheet portrait of {who}. Full figure, friendly pose, neutral background, even light"
    parts = [look, what, el.get("style_anchor") or ""]
    return ". ".join(t for t in (p.strip().rstrip(".") for p in parts) if t)


def reference_urls(pid: str, el: dict) -> list[str]:
    urls: list[str] = []
    for rel in el.get("references") or []:
        if safe_rel(pid, rel, plan.IMAGE_EXT) and len(urls) < MAX_REFERENCES:
            ext = rel.rsplit(".", 1)[-1].lower()
            urls.append(f"data:{_MIME.get(ext, 'image/png')};base64," + base64.b64encode((project_root(pid) / rel).read_bytes()).decode("ascii"))
    return urls


def _work(pid: str, el_id: str) -> dict:
    el = _element(pid, el_id)
    model = plan.get_head(pid)["models"]["image"] or image_provider.server_default_model()
    prompt = build_prompt(pid, el)
    try:
        raw = image_provider.request_image(model=model, prompt=prompt, references=reference_urls(pid, el), aspect_ratio=ASPECT)
    except image_provider.ProviderError as e:
        raise jobs.JobFailed(str(e)) from e
    ext = image_provider.image_kind(raw)
    if ext is None:
        raise jobs.JobFailed("bad_image")
    name = f"{new_id()}.{ext}"
    target = root(pid, create=True) / "media" / "probes" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    created = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    write_json(target.with_name(name + ".json"), {"prompt": prompt, "model": model, "element_id": el_id, "created_at": created})
    rel = f"{PROBE_DIR}{name}"
    with project_lock(pid):                                  # Baustein frisch lesen – der Nutzer kann inzwischen geändert haben
        path = root(pid) / "elements" / el_id / "element.json"
        cur = read_json(path, None)
        if not isinstance(cur, dict):
            raise jobs.JobFailed("element_gone")
        write_json(path, {**cur, "probe_rel": rel, "approved": False})
    return {"probe_rel": rel, "model": model}


def start(pid: str, el_id: str) -> dict:
    el = _element(pid, el_id)                                # 404 vor dem Auftrag
    if not el.get("description") and not reference_urls(pid, el):
        raise plan.PlanError("studio_probe_nothing")
    return jobs.start(pid, "probe", el_id, "", lambda: _work(pid, el_id), busy_code="studio_probe_running")
