"""Was an die Bild-KI geht (Spec „Bauplan H“): Auftrag, Vorlagen, Startwert – wie im Atelier, berechenbar.

- H3: Look → je Figur „Name: Aussehen“ → Orte → Dinge → der Text des Nutzers → Kamera. Nur Angehakte (cast.of_shot).
- H4: fester Startwert der ersten Figur; „anderes Bild“ (`fresh`) nimmt bewusst einen neuen.
- H6: „Bild ändern“: das gezeigte Bild ist die erste Vorlage, dazu der Änderungswunsch.
"""
from __future__ import annotations

import base64
import secrets

from . import cast, plan, presets
from ._clean import CAMERA_KEYS
from ._store import project_root, safe_rel

MAX_REFERENCES = 3           # mehr nehmen manche Modelle nicht an (HTTP 400)
MAX_CHANGE = 1000
_MIME = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp", "gif": "image/gif"}


def cast_of(pid: str, scene: dict, shot: dict) -> list[dict]:
    els = plan.list_elements(pid)
    by_id = {e["id"]: e for e in els}
    return [by_id[i] for i in cast.of_shot(scene, shot, els)]


def _clean(t: str) -> str:
    return t.strip().rstrip(".").strip()


def build_prompt(pid: str, scene: dict, shot: dict, change: str = "") -> str:
    head = plan.get_head(pid)
    parts: list[str] = [head["look"]["style"]]
    palette = list(head["look"]["palette"])
    for e in cast_of(pid, scene, shot):
        desc = e.get("description") or ""
        parts.append(f"{e['name']}: {desc}" if desc else e["name"])
        parts.append(e.get("style_anchor") or "")
        palette += [c for c in e.get("palette") or [] if c not in palette]
    if palette:
        parts.append("color palette: " + ", ".join(palette[:12]))
    parts.append(shot.get("prompt") or "")
    if shot.get("shot"):
        parts.append(presets.phrase_for("shot", shot["shot"]) or "")
    cam = scene.get("camera") or {}
    parts += [presets.phrase_for(k, cam[k]) or "" for k in CAMERA_KEYS if k != "shot" and cam.get(k)]
    if change:
        parts.append(f"Change only this in the first reference image: {change}. Keep everything else exactly as it is "
                     "(characters, their looks, place, light, style)")
    return ". ".join(t for t in (_clean(p) for p in parts) if t)


def _data_url(pid: str, rel: str) -> str:
    ext = rel.rsplit(".", 1)[-1].lower()
    return f"data:{_MIME.get(ext, 'image/png')};base64," + base64.b64encode((project_root(pid) / rel).read_bytes()).decode("ascii")


def reference_urls(pid: str, shot: dict, scene: dict | None = None, *, base_image: str = "") -> list[str]:
    """Vorlagen: (H6) das gezeigte Bild zuerst, dann je Figur das freigegebene Probebild bzw. die Fotos – höchstens 3."""
    rels = [base_image] if base_image else []
    for e in cast_of(pid, scene or {}, shot):
        first = [e["probe_rel"]] if e.get("approved") and e.get("probe_rel") else []      # G2: Probebild zuerst
        rels += first + list(e.get("references") or [])
    urls: list[str] = []
    for rel in dict.fromkeys(rels):
        if safe_rel(pid, rel, plan.IMAGE_EXT):
            urls.append(_data_url(pid, rel))
            if len(urls) >= MAX_REFERENCES:
                break
    return urls


def seed_of(pid: str, scene: dict, shot: dict, *, fresh: bool = False) -> int | None:
    """Startwert der ersten Figur (H4); ohne Figur keiner; `fresh` = bewusst ein neuer."""
    people = [e for e in cast_of(pid, scene, shot) if e.get("kind") == "character"]
    if fresh:
        return secrets.randbelow(2**31)
    s = people[0].get("seed") if people else None
    return s if isinstance(s, int) and not isinstance(s, bool) else None


def check_change(change) -> str:
    if not isinstance(change, str) or not change.strip() or len(change) > MAX_CHANGE:
        raise plan.PlanError("studio_change_invalid")
    return change.strip()
