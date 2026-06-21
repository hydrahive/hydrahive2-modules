"""Bild-Auswahl für den Report: Hero + Sektions-Bilder aus den OG-Images der Quellen."""
from __future__ import annotations

import re

_BAD_EXT = (".svg", ".ico", ".gif")
_ICONISH = re.compile(r"(favicon|sprite|logo|icon|avatar|placeholder|1x1|pixel)", re.IGNORECASE)


def _usable(url: str) -> bool:
    if not url or not url.startswith(("http://", "https://")):
        return False
    low = url.lower().split("?")[0]
    if low.endswith(_BAD_EXT):
        return False
    if _ICONISH.search(url):
        return False
    return True


def pick_images(sources: list[dict]) -> tuple[str, list[str]]:
    """(hero, sektions_bilder) — dedupliziert, nur brauchbare http(s)-Bilder."""
    seen: set[str] = set()
    images: list[str] = []
    for s in sources:
        img = (s.get("image") or "").strip()
        if img and img not in seen and _usable(img):
            seen.add(img)
            images.append(img)
    if not images:
        return "", []
    return images[0], images[1:]
