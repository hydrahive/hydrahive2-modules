"""Atelier — Generierungs-Orchestrierung.

Verbindet CI-Kit + Charaktere + Szene zu einem Image-API-Call und persistiert
Ergebnis + Sidecar-Metadaten. Bewusst getrennt von routes.py (HTTP) und
generate.py (API-Client), damit die Kette ohne FastAPI testbar bleibt.
"""
from __future__ import annotations

import base64
import json
import mimetypes
from datetime import datetime, timezone

from . import characters, generate, presets, storage


def file_to_data_url(path) -> str:
    """Lokale Bilddatei → data:-URL (base64) für input_references der Image-API."""
    mime, _ = mimetypes.guess_type(str(path))
    b64 = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime or 'image/png'};base64,{b64}"


def _gallery_dirs(project_id: str) -> list[tuple[str, object]]:
    """Neue Bildablage zuerst, Legacy-output danach."""
    return [("images", storage.images_dir(project_id)), ("output", storage.output_dir(project_id))]


def _is_gallery_image_path(project_id: str, img) -> bool:
    return any(img.parent == d for _, d in _gallery_dirs(project_id))


def delete_gallery_image(project_id: str, rel: str) -> bool:
    """Löscht ein generiertes Bild + Sidecar aus images/ oder Legacy-output/."""
    root = storage.atelier_root(project_id)
    img = storage.safe_under(root, rel)
    if img is None or not img.is_file() or not _is_gallery_image_path(project_id, img):
        return False
    img.unlink(missing_ok=True)
    img.with_suffix(img.suffix + ".json").unlink(missing_ok=True)
    return True


def scan_gallery(project_id: str) -> list[dict]:
    """Generierte Bilder des Projekts (neueste zuerst) + Sidecar-Metadaten.

    Liest neue Bilder aus images/ und alte Bestände weiterhin aus output/.
    """
    items: list[dict] = []
    for rel_dir, out_dir in _gallery_dirs(project_id):
        for img in out_dir.iterdir():
            if img.suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp"):
                continue
            meta_path = img.with_suffix(img.suffix + ".json")
            meta = {}
            if meta_path.is_file():
                try:
                    meta = json.loads(meta_path.read_text("utf-8"))
                except (json.JSONDecodeError, OSError):
                    meta = {}
            items.append({
                "name": img.name,
                "path": str(img),
                "rel": f"{rel_dir}/{img.name}",
                "created_at": meta.get("created_at"),
                "prompt": meta.get("prompt"),
                "seed": meta.get("seed"),
                "model": meta.get("model"),
                # Felder für "Wiederholen": vorbefüllen des Generieren-Tabs.
                "scene": meta.get("scene"),
                "character_ids": meta.get("character_ids") or [],
                "aspect_ratio": meta.get("aspect_ratio"),
                "camera": meta.get("camera") or {},
                "style": meta.get("style"),
                "mtime": img.stat().st_mtime,
            })
    items.sort(key=lambda i: i["mtime"], reverse=True)
    return items

_DEFAULT_MODEL = "google/gemini-2.5-flash-image"
# OpenRouter-Image-API begrenzt input_references je Modell (gemini: 0-3).
# 3 ist der sichere modellübergreifende Höchstwert; mehr → HTTP 400.
_MAX_REFERENCES = 3


def generate_for_project(project_id: str, req: dict) -> dict:
    """Führt eine Generierung für ein Projekt aus. Wirft GenerateError bei Fehler.

    req: { scene, character_ids[], model?, seed?, aspect_ratio?, camera{group:key} }
    Rückgabe: das Galerie-Item (name, rel, prompt, seed, model, created_at).
    """
    ci = characters.get_ci(project_id)
    chosen = _resolve_characters(project_id, req.get("character_ids") or [])

    model = (req.get("model") or "").strip() or ci.get("default_model") or _DEFAULT_MODEL
    aspect = (req.get("aspect_ratio") or "").strip() or ci.get("aspect_ratio") or "1:1"
    seed = _resolve_seed(req.get("seed"), chosen)

    camera_sel = req.get("camera") or {}
    camera_phrases = presets.collect_phrases(camera_sel) if isinstance(camera_sel, dict) else []
    style_key = str(req.get("style") or "")
    style_phrase = presets.style_phrase(style_key) if style_key else None
    prompt = generate.build_prompt(
        req.get("scene") or "",
        ci_anchor=ci.get("style_anchor") or "",
        characters=chosen,
        camera=camera_phrases,
        style=style_phrase,
    )
    references = _collect_reference_urls(project_id, chosen)

    raw = generate.generate_image(
        model=model,
        prompt=prompt,
        references=references,
        seed=seed,
        aspect_ratio=aspect,
    )

    ext = _sniff_ext(raw)
    created = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rel = storage.save_image_bytes(project_id, raw, ext=ext, prompt=req.get("scene") or prompt)
    name = rel.rsplit("/", 1)[-1]
    meta = {
        "prompt": prompt,
        "scene": req.get("scene") or "",
        "character_ids": [c["id"] for c in chosen],
        "seed": seed,
        "model": model,
        "aspect_ratio": aspect,
        "references": [c["id"] for c in chosen if c.get("references")],
        "camera": camera_sel,
        "style": style_key,
        "created_at": created,
    }
    _write_sidecar(project_id, rel, meta)

    return {
        "name": name,
        "rel": rel,
        "path": str(storage.atelier_root(project_id) / rel),
        "prompt": prompt,
        "seed": seed,
        "model": model,
        "created_at": created,
    }


def _resolve_characters(project_id: str, ids: list[str]) -> list[dict]:
    out: list[dict] = []
    for cid in ids[:6]:
        ch = characters.get_character(project_id, cid)
        if ch is not None:
            out.append(ch)
    return out


def _resolve_seed(req_seed, chosen: list[dict]) -> int | None:
    if isinstance(req_seed, int):
        return req_seed
    for ch in chosen:
        if isinstance(ch.get("seed"), int):
            return ch["seed"]
    return None


def _collect_reference_urls(project_id: str, chosen: list[dict]) -> list[str]:
    """Hero-Referenzbilder aller gewählten Figuren als data:-URLs.

    Gekappt auf ``_MAX_REFERENCES``: die OpenRouter-Image-API akzeptiert je
    Modell nur eine begrenzte Zahl an input_references (gemini: 0-3). Mehr
    führt zu HTTP 400. 3 ist der sichere, modellübergreifende Höchstwert.
    """
    urls: list[str] = []
    root = storage.atelier_root(project_id)
    for ch in chosen:
        for rel in ch.get("references") or []:
            p = storage.safe_under(root, rel)
            if p is not None and p.is_file():
                urls.append(file_to_data_url(p))
            if len(urls) >= _MAX_REFERENCES:
                return urls
    return urls


def _write_sidecar(project_id: str, rel: str, meta: dict) -> None:
    path = storage.safe_under(storage.atelier_root(project_id), rel)
    if path is None:
        raise ValueError("invalid_gallery_path")
    path.with_suffix(path.suffix + ".json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), "utf-8"
    )


def write_image_sidecar(project_id: str, rel: str, meta: dict) -> None:
    """Öffentlicher Wrapper: Sidecar für ein Galerie-Bild (z.B. Fortsetzungs-Frame)."""
    meta.setdefault("created_at", datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    _write_sidecar(project_id, rel, meta)


def _sniff_ext(raw: bytes) -> str:
    if raw[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if raw[:3] == b"\xff\xd8\xff":
        return "jpg"
    if raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
        return "webp"
    return "png"
