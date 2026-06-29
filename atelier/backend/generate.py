"""Atelier — Bild-Generierung über OpenRouters dedizierte Image-API.

Eigener Client (Variante b): nutzt ``POST /api/v1/images`` mit den starken
Konsistenz-Hebeln, ohne das Core-``generate_image`` (chat-Pfad) anzufassen.

Verifiziert gegen die Live-API (2026-06):
  Request   { model, prompt, input_references:[{type:"image_url",
              image_url:{url}}], seed?, aspect_ratio? }
  Response  { data:[{ b64_json }], usage:{ cost } }

Referenzbilder können ALLE Image-Modelle (stärkster Hebel). ``seed`` nur
wenige (flux.2, seedream-4.5) — wird nur mitgeschickt, wenn gesetzt.
"""
from __future__ import annotations

import base64
import binascii

import httpx

from hydrahive.llm._config import openrouter_key

_URL = "https://openrouter.ai/api/v1/images"
_TIMEOUT = 180.0


class GenerateError(RuntimeError):
    """Generierung fehlgeschlagen (Key fehlt, API-Fehler, leere Antwort)."""


def build_prompt(
    scene: str,
    *,
    ci_anchor: str,
    characters: list[dict],
    camera: list[str] | None = None,
) -> str:
    """Baut den vollen Prompt: CI-Anker + Figur-Steckbriefe (verbatim) + Szene
    + Regie-/Kamera-Spezifikation.

    Reihenfolge bewusst: zuerst der feste Stil (CI), dann die Figuren wörtlich,
    dann das Variable (Szene), zuletzt die Aufnahme-Spezifikation (Kamera, Licht,
    Wetter …). So bleibt der konsistente Teil dominant, die Regie modifiziert.
    """
    parts: list[str] = []
    if ci_anchor.strip():
        parts.append(ci_anchor.strip())
    for ch in characters:
        desc = (ch.get("description") or "").strip()
        name = (ch.get("name") or "").strip()
        if desc:
            parts.append(f"{name}: {desc}" if name else desc)
        elif name:
            parts.append(name)
        anchor = (ch.get("style_anchor") or "").strip()
        if anchor:
            parts.append(anchor)
    palette = _collect_palette(ci_anchor, characters)
    if palette:
        parts.append("color palette: " + ", ".join(palette))
    if scene.strip():
        parts.append(scene.strip())
    for phrase in camera or []:
        parts.append(phrase)
    return ". ".join(parts)


def _collect_palette(ci_anchor: str, characters: list[dict]) -> list[str]:
    seen: list[str] = []
    for ch in characters:
        for c in ch.get("palette") or []:
            if c and c not in seen:
                seen.append(c)
    return seen[:8]


def _ref_block(url: str) -> dict:
    return {"type": "image_url", "image_url": {"url": url}}


def generate_image(
    *,
    model: str,
    prompt: str,
    references: list[str] | None = None,
    seed: int | None = None,
    aspect_ratio: str = "1:1",
) -> bytes:
    """Generiert ein Bild und gibt die rohen Bytes zurück (PNG/JPEG).

    ``references``: Liste von http(s)- oder data:-URLs (Hero-Referenzbilder).
    Wirft ``GenerateError`` bei Key-Mangel, HTTP-/API-Fehler oder leerer Antwort.
    """
    key = openrouter_key()
    if not key:
        raise GenerateError("Kein OpenRouter-API-Key konfiguriert.")

    payload: dict = {"model": model, "prompt": prompt, "aspect_ratio": aspect_ratio}
    if references:
        payload["input_references"] = [_ref_block(u) for u in references if u]
    if seed is not None:
        payload["seed"] = seed

    try:
        resp = httpx.post(
            _URL,
            json=payload,
            headers={"Authorization": f"Bearer {key}"},
            timeout=_TIMEOUT,
        )
    except httpx.HTTPError as e:
        raise GenerateError(f"Netzwerkfehler bei der Generierung: {e}") from e

    if resp.status_code != 200:
        raise GenerateError(_describe_http_error(resp))

    return _extract_image(resp.json())


def _describe_http_error(resp: httpx.Response) -> str:
    detail = ""
    try:
        body = resp.json()
        detail = body.get("error", {}).get("message") or str(body)[:300]
    except (ValueError, AttributeError):
        detail = resp.text[:300]
    return f"Image-API antwortete {resp.status_code}: {detail}"


def _extract_image(body: dict) -> bytes:
    data = body.get("data")
    if not isinstance(data, list) or not data:
        raise GenerateError("Image-API lieferte keine Bilddaten.")
    b64 = data[0].get("b64_json") or ""
    if not b64:
        url = data[0].get("url")
        if url:
            raise GenerateError("Image-API lieferte eine URL statt base64 — nicht unterstützt.")
        raise GenerateError("Image-API lieferte ein leeres Bild.")
    try:
        return base64.b64decode(b64, validate=True)
    except (binascii.Error, ValueError) as e:
        raise GenerateError(f"Bilddaten nicht dekodierbar: {e}") from e
