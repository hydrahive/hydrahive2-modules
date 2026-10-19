"""Vorlagen für die Ausgabe (Spec „7b im Detail“): Format + Qualität → Bildgröße und Kodierung. Reine Funktionen.

Die Qualität ist immer die kürzere Seite; die längere ergibt sich aus dem Format und wird auf eine gerade Zahl gerundet
(H.264 mit yuv420p braucht gerade Maße). Gleiche Tabelle im Frontend (frontend/deliverLogic.ts, Gleichheit getestet).
"""
from __future__ import annotations

RATIOS = {"16:9": (16, 9), "9:16": (9, 16), "1:1": (1, 1), "4:3": (4, 3), "21:9": (21, 9)}
DEFAULT_ASPECT = "16:9"
ASPECTS = ("screenplay", "16:9", "9:16", "1:1")          # wählbar; „screenplay“ = Format des Drehbuchs
QUALITIES = {"preview": (480, 28), "standard": (720, 23), "high": (1080, 20)}   # kürzere Seite, crf
DEFAULT_QUALITY = "standard"


def _even(x: float) -> int:
    return round(x / 2) * 2


def size(aspect: str, quality: str) -> tuple[int, int]:
    rw, rh = RATIOS.get(aspect, RATIOS[DEFAULT_ASPECT])
    short = QUALITIES.get(quality, QUALITIES[DEFAULT_QUALITY])[0]
    if rw >= rh:
        return _even(short * rw / rh), short
    return short, _even(short * rh / rw)


def resolve(aspect, quality, screenplay_aspect: str) -> dict:
    """Gewählte Vorlage prüfen und auflösen. None = Standard. Unbekannt → ValueError."""
    if aspect is None:
        aspect = "screenplay"
    if quality is None:
        quality = DEFAULT_QUALITY
    if aspect not in ASPECTS or not isinstance(quality, str) or quality not in QUALITIES:   # Liste o. Ä. nie als Schlüssel
        raise ValueError("unbekannte Vorlage")
    real = screenplay_aspect if aspect == "screenplay" else aspect
    if real not in RATIOS:
        real = DEFAULT_ASPECT
    return {"aspect": real, "quality": quality, "size": size(real, quality), "crf": QUALITIES[quality][1]}
