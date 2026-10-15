"""Status des Vitrine-Dienstes aus <daten>/state.json (der Dienst schreibt sie, das Backend liest nur)."""
from __future__ import annotations

import json
import time
from pathlib import Path

STALE_SECONDS = 20.0            # Dienst schreibt spätestens alle 5 s; danach gilt er als gestoppt
_last: dict[str, tuple[float, int]] = {}


def reset_rate() -> None:
    _last.clear()


def read(data_dir: Path, *, now: float | None = None) -> dict:
    now = time.time() if now is None else now
    out = {"running": False, "connected": False, "frames": 0, "fps": None, "video": None, "error": None, "size": None}
    try:
        raw = json.loads((data_dir / "state.json").read_text())
    except (OSError, ValueError):
        return out
    updated = float(raw.get("updated") or 0)
    if now - updated > STALE_SECONDS:
        return {**out, "frames": int(raw.get("frames") or 0)}
    frames = int(raw.get("frames") or 0)
    key = str(data_dir)
    fps = None
    if key in _last and updated > _last[key][0]:
        t0, f0 = _last[key]
        fps = round((frames - f0) / (updated - t0), 1)
    _last[key] = (updated, frames)
    return {"running": True, "connected": bool(raw.get("connected")), "frames": frames, "fps": fps,
            "video": raw.get("video"), "error": raw.get("error"), "size": raw.get("size")}


def program_info(data_dir: Path) -> dict:
    """Programm-Felder aus state.json (rule, holiday, night) – schreibt der Dienst."""
    try:
        raw = json.loads((data_dir / "state.json").read_text())
    except (OSError, ValueError):
        return {"rule": None, "holiday": None, "night": None}
    return {k: raw.get(k) for k in ("rule", "holiday", "night")}
