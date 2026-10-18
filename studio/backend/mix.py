"""Mischpult des Studios (Spec „Bauplan 5b“): Werte prüfen, wer klingt, Ducking-Kurve. Rein, ohne ffmpeg.

Ducking als feste Kurve statt Kompressor: Vorschau (frontend/mixLogic.ts) und Film rechnen dieselbe Formel, daher klingt
beides gleich und es ist exakt prüfbar. Die Musik sinkt RAMP_DOWN Sekunden vor einem Sprachzeitraum auf DUCK_DB und
kehrt danach in RAMP_UP Sekunden zurück; Übergänge linear in dB.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

GAIN_MIN, GAIN_MAX = -60.0, 12.0
DUCK_DB = -12.0
RAMP_DOWN, RAMP_UP = 0.2, 0.6
MERGE_GAP = 0.8                    # Sprachpausen darunter heben die Musik nicht kurz an
MAX_SPANS = 300                    # Grenze für den Ausdruck im Filtergraphen
TRACK_KEYS = ("gain_db", "mute", "solo")


class Bad(ValueError):
    """Ungültiger Mischpult-Wert."""


def gain(v: Any) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or not GAIN_MIN <= v <= GAIN_MAX:
        raise Bad()
    return v


def flag(v: Any) -> bool:
    if not isinstance(v, bool):
        raise Bad()
    return v


def track_values(raw: dict, *, strict: bool) -> dict:
    """Mischpult-Werte einer Spur; nur Abweichungen vom Standard. `strict=False` (Laden): Ungültiges fällt weg."""
    out: dict = {}
    for key, check, default in (("gain_db", gain, 0), ("mute", flag, False), ("solo", flag, False)):
        if key not in raw:
            continue
        try:
            v = check(raw[key])
        except Bad:
            if strict:
                raise
            continue
        if v != default:
            out[key] = v
    return out


def clip_values(raw: dict, length: float, *, strict: bool) -> dict:
    """Lautstärke und Blenden eines Tonclips; Blenden zusammen höchstens die Cliplänge."""
    out: dict = {}
    for key in ("gain_db", "fade_in", "fade_out"):
        if key not in raw:
            continue
        v = raw[key]
        ok = (not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)
              and (GAIN_MIN <= v <= GAIN_MAX if key == "gain_db" else v >= 0))
        if not ok:
            if strict:
                raise Bad()
            continue
        if v != 0:
            out[key] = v
    if out.get("fade_in", 0) + out.get("fade_out", 0) > length + 1e-6:
        if strict:
            raise Bad()
        out.pop("fade_in", None)
        out.pop("fade_out", None)
    return out


def audible(tracks: dict[str, dict]) -> set[str]:
    """Spuren, die klingen: mit Solo nur die Solo-Spuren (Solo schlägt Stumm), sonst alle nicht stummen."""
    solo = {k for k, v in tracks.items() if v.get("solo")}
    return solo or {k for k, v in tracks.items() if not v.get("mute")}


def duck_spans(spans: list[list[float]] | list[tuple[float, float]]) -> list[list[float]]:
    """Sprachzeiträume sortiert und zusammengelegt (Abstand < MERGE_GAP); höchstens MAX_SPANS (dann gröber)."""
    out: list[list[float]] = []
    gap = MERGE_GAP
    while True:
        out = []
        for a, b in sorted((float(a), float(b)) for a, b in spans):
            if out and a - out[-1][1] < gap:
                out[-1][1] = max(out[-1][1], b)
            else:
                out.append([a, b])
        if len(out) <= MAX_SPANS:
            return out
        gap *= 2


def _db(t: float, a: float, b: float) -> float:
    """dB-Absenkung eines Zeitraums [a, b] bei t (0 = keine)."""
    if t < a - RAMP_DOWN or t > b + RAMP_UP:
        return 0.0
    if t < a:
        return DUCK_DB * (t - (a - RAMP_DOWN)) / RAMP_DOWN
    if t <= b:
        return DUCK_DB
    return DUCK_DB * (1 - (t - b) / RAMP_UP)


def duck_factor(spans: list[list[float]], t: float) -> float:
    db = min((_db(t, a, b) for a, b in spans), default=0.0)
    return 10 ** (db / 20)


def duck_expr(spans: list[list[float]]) -> str:
    """Dieselbe Kurve als ffmpeg-Ausdruck für `volume=…:eval=frame` (t = Zeit im Film)."""
    if not spans:
        return "1"
    terms = []
    for a, b in spans:
        d0, u1 = a - RAMP_DOWN, b + RAMP_UP
        terms.append(f"if(lt(t,{d0:.3f}),0,if(lt(t,{a:.3f}),{DUCK_DB}*(t-{d0:.3f})/{RAMP_DOWN},"
                     f"if(lt(t,{b:.3f}),{DUCK_DB},if(lt(t,{u1:.3f}),{DUCK_DB}*(1-(t-{b:.3f})/{RAMP_UP}),0))))")
    db = terms[0]
    for x in terms[1:]:
        db = f"min({db},{x})"
    return f"pow(10,({db})/20)"


@dataclass
class Mixer:
    """Mischpult-Einstellungen der Fassung. Standard = Verhalten aus 5a (nichts verändert)."""
    tracks: dict[str, dict] = field(default_factory=lambda: {"V1": {}, "A1": {}, "A2": {}})
    duck: bool = True

    @classmethod
    def of(cls, tl: dict) -> Mixer:
        return cls(tracks={t["id"]: {k: t[k] for k in TRACK_KEYS if k in t} for t in tl["tracks"]}, duck=tl.get("duck", True) is not False)

    def hears(self, track: str) -> bool:
        return track in audible(self.tracks)

    def track_gain(self, track: str) -> float:
        return float(self.tracks.get(track, {}).get("gain_db", 0))
