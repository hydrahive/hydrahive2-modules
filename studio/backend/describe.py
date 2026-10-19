"""Baustein aus seinem Foto beschreiben (Spec „C2 im Detail“): Beschreibung + Aussehen von der Bild-KI.

Antwort als JSON {"description", "style_anchor"} (Codeblock wird abgezogen). Nur bei brauchbarer Antwort wird gespeichert;
sonst bleibt der Baustein unverändert. Kosten ≈ 0,1 ct je Foto.
"""
from __future__ import annotations

import base64
import json

from . import _clean, plan, vision_provider
from ._store import project_root, safe_rel

KIND_WORD = {"character": "Figur", "place": "Ort", "item": "Gegenstand"}
MIME = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp", "gif": "image/gif"}
CODES = {"no_key": ("studio_describe_no_key", 400)}


def prompt_for(el: dict) -> str:
    word = KIND_WORD.get(el.get("kind"), "Figur")
    return (f"Das Foto zeigt die {word} „{el.get('name') or ''}“ für einen Film. Antworte NUR mit JSON: "
            '{"description": "<2–4 Sätze auf Deutsch: wer oder was das ist, Wirkung, Rolle>", '
            '"style_anchor": "<feste Merkmale auf Englisch, kommagetrennt, die in jedem Bild gleich bleiben müssen: '
            'Gestalt, Gesicht/Form, Farben, Kleidung bzw. Material und Bauweise>"}. Keine Erklärungen.')


def parse(raw: str) -> dict:
    s = raw.strip()
    if s.startswith("```"):
        s = s.split("\n", 1)[1] if "\n" in s else ""
        s = s.rsplit("```", 1)[0]
    try:
        data = json.loads(s)
    except ValueError as e:
        raise plan.PlanError("studio_describe_failed", 502) from e
    desc = _clean.text(data.get("description"), 4000) if isinstance(data, dict) else ""
    if not desc:
        raise plan.PlanError("studio_describe_failed", 502)
    return {"description": desc, "style_anchor": _clean.text(data.get("style_anchor"), 2000)}


def _image_url(pid: str, el: dict) -> str:
    rel = next((r for r in el.get("references") or [] if safe_rel(pid, r, plan.IMAGE_EXT)), None)
    if not rel:
        raise plan.PlanError("studio_describe_no_image")
    ext = rel.rsplit(".", 1)[-1].lower()
    return f"data:{MIME.get(ext, 'image/png')};base64," + base64.b64encode((project_root(pid) / rel).read_bytes()).decode("ascii")


async def describe(pid: str, el_id: str) -> dict:
    el = next((e for e in plan.list_elements(pid) if e["id"] == el_id), None)
    if el is None:
        raise plan.PlanError("studio_not_found", 404)
    model = plan.get_head(pid)["models"].get("vision") or vision_provider.DEFAULT_MODEL
    try:
        raw = await vision_provider.ask(model=model, image_url=_image_url(pid, el), prompt=prompt_for(el))
    except vision_provider.VisionError as e:
        code, status = CODES.get(str(e), ("studio_describe_failed", 502))
        raise plan.PlanError(code, status) from e
    return plan.save_element(pid, {**el, **parse(raw)}, el_id)


def from_image(pid: str, data: dict) -> dict:
    """Neuen Baustein mit einem Bild aus dem Projekt als Vorlage anlegen (Bibliothek → „Als Figur anlegen …“)."""
    rel = safe_rel(pid, data.get("rel"), plan.IMAGE_EXT)
    if not rel or data.get("kind") not in _clean.ELEMENT_KINDS or not _clean.text(data.get("name"), 200):
        raise plan.PlanError("studio_element_invalid")
    return plan.save_element(pid, {"kind": data["kind"], "name": data["name"], "references": [rel]})
