"""Prüfregeln für Planungsdaten (Längen und gültige Werte wie im Atelier, Spec „Bauplan Etappe 2“)."""
from __future__ import annotations

from typing import Any

from . import presets
from ._store import is_id, new_id

ELEMENT_KINDS = ("character", "place", "object")
SHOT_STATUS = ("planned", "image_ready", "video_processing", "done", "failed")
MODEL_KEYS = ("video", "image", "voice", "music", "text", "vision")
LANGUAGES = ("de", "en", "fr", "es", "it", "nl", "pl", "pt", "tr", "uk", "ru", "sv", "da", "no", "fi", "cs", "ja", "zh")
CAMERA_KEYS = ("shot", "lens", "light", "weather", "time", "mood")
VARIANT_DIRS = ("studio/media/images/", "studio/media/free/")
PROBE_DIR = "studio/media/probes/"                                  # Probebilder der Bausteine (G2)
VOICE_DIR = "studio/media/voice/"                                   # erzeugte Sprache je Shot (5c)    # Bilder des Studios: je Shot erzeugt oder frei (B3)


def text(v: Any, n: int) -> str:
    return str(v or "").strip()[:n] if v is not None and not isinstance(v, (dict, list)) else ""


def num(v: Any, lo: int, hi: int, default: int) -> int:
    try:
        return max(lo, min(hi, int(v)))
    except (TypeError, ValueError):
        return default


def palette(v: Any) -> list[str]:
    return [text(c, 20) for c in (v if isinstance(v, list) else []) if text(c, 20)][:12]


def ids(v: Any, allowed: set[str] | None = None, limit: int = 32) -> list[str]:
    out = []
    for x in v if isinstance(v, list) else []:
        if is_id(x) and x not in out and (allowed is None or x in allowed):
            out.append(x)
    return out[:limit]


def head(data: dict, *, scene_order: list[str]) -> dict:
    models = data.get("models") if isinstance(data.get("models"), dict) else {}
    look = data.get("look") if isinstance(data.get("look"), dict) else {}
    return {
        "title": text(data.get("title"), 200),
        "logline": text(data.get("logline"), 500),
        "description": text(data.get("description"), 4000),
        "aspect_ratio": text(data.get("aspect_ratio"), 16) or "16:9",
        "language": data["language"] if data.get("language") in LANGUAGES else "de",   # Sprache des Films (Untertitel, 6)
        "default_duration": num(data.get("default_duration"), 1, 60, 5),
        "models": {k: text(models.get(k), 200) for k in MODEL_KEYS},
        "look": {"style": text(look.get("style"), 2000), "palette": palette(look.get("palette"))},
        "scene_order": scene_order,
    }


def camera(v: Any) -> dict:
    v = v if isinstance(v, dict) else {}
    return {k: v[k] for k in CAMERA_KEYS if isinstance(v.get(k), str) and presets.phrase_for(k, v[k])}


def dialogue(v: Any, elements: set[str]) -> dict | None:
    if not isinstance(v, dict) or not text(v.get("line"), 2000):
        return None
    el = v.get("element_id")
    return {"element_id": el if el in elements else "", "line": text(v.get("line"), 2000), "emotion": text(v.get("emotion"), 50)}


def shot(v: Any, order: int, elements: set[str]) -> dict:
    v = v if isinstance(v, dict) else {}
    status = v.get("status") if v.get("status") in SHOT_STATUS else "planned"
    key = v.get("shot") if isinstance(v.get("shot"), str) and presets.phrase_for("shot", v["shot"]) else ""
    return {
        "id": v["id"] if is_id(v.get("id")) else new_id(), "order": order, "shot": key,
        "prompt": text(v.get("prompt"), 2000), "element_ids": ids(v.get("element_ids"), elements),
        "excluded_ids": ids(v.get("excluded_ids"), elements),           # G3: „Mit dabei“ abgewählt (auch wenn genannt)
        "duration": num(v.get("duration"), 1, 60, 5), "status": status,
        "image_rel": v["image_rel"] if isinstance(v.get("image_rel"), str) else None,
        "video_rel": v["video_rel"] if isinstance(v.get("video_rel"), str) else None,
        "variants": [x for x in (v.get("variants") if isinstance(v.get("variants"), list) else [])
                     if isinstance(x, str) and x.startswith(VARIANT_DIRS) and ".." not in x][-8:],
        # 5c: Sprechtext, Stimme (leer = Standard des Modells) und erzeugte Sprache
        "speech": text(v.get("speech"), 1000), "voice": text(v.get("voice"), 100),
        "voice_rel": v["voice_rel"] if isinstance(v.get("voice_rel"), str) and v["voice_rel"].startswith(VOICE_DIR)
                     and ".." not in v["voice_rel"] else None,
    }


def scene(scene_id: str, data: dict, elements: set[str], *, shots: list | None = None) -> dict:
    dl = [d for d in (dialogue(x, elements) for x in (data.get("dialogues") or [])) if d][:100]
    raw_shots = data.get("shots") if shots is None else shots
    return {
        "id": scene_id,
        "title": text(data.get("title"), 200),
        "description": text(data.get("description"), 4000),
        "location": text(data.get("location"), 200),
        "time_of_day": text(data.get("time_of_day"), 50),
        "element_ids": ids(data.get("element_ids"), elements),
        "dialogues": dl,
        "camera": camera(data.get("camera")),
        "shots": [shot(s, i, elements) for i, s in enumerate(raw_shots if isinstance(raw_shots, list) else [])][:50],
    }


def element(el_id: str, data: dict, references: list[str]) -> dict:
    return {
        "id": el_id,
        "kind": data.get("kind"),
        "name": text(data.get("name"), 200),
        "description": text(data.get("description"), 4000),
        "style_anchor": text(data.get("style_anchor"), 2000),
        "palette": palette(data.get("palette")),
        "references": references[:8],
        # G2: Probebild + Freigabe + „Kein Foto“. Probebild nur aus dem eigenen Ordner, Freigabe nur mit Probebild.
        "probe_rel": probe(data.get("probe_rel")),
        "approved": data.get("approved") is True and bool(probe(data.get("probe_rel"))),
        "no_photo": data.get("no_photo") is True,
    }


def probe(v: Any) -> str:
    ok = isinstance(v, str) and v.startswith(PROBE_DIR) and "/" not in v[len(PROBE_DIR):] and ".." not in v and len(v) <= 200
    return v if ok else ""
