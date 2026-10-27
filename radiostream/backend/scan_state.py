"""Stand des Einlesens (im Speicher; nur ein Durchgang zugleich). Für Fortschrittsanzeige und Abbrechen."""
from __future__ import annotations

import threading
import time
from datetime import datetime, timezone

_lock = threading.Lock()
_state: dict = {}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def reset() -> None:
    with _lock:
        _state.clear()
        _state.update(running=False, cancel=False, started_at=None, finished_at=None, dirs_seen=0, files_seen=0,
                      todo=0, done=0, added=0, updated=0, unchanged=0, missing=0, errors=0, error_code=None,
                      _t0=None)


reset()


def try_begin() -> bool:
    with _lock:
        if _state["running"]:
            return False
        # Ein neuer Durchgang beginnt immer ohne Abbruch-Wunsch (ein „Abbrechen“ ohne laufenden Durchgang
        # darf den nächsten nicht sofort stoppen).
        _state.update({"running": True, "started_at": _now(), "finished_at": None, "dirs_seen": 0, "files_seen": 0,
                       "todo": 0, "done": 0, "added": 0, "updated": 0, "unchanged": 0, "missing": 0, "errors": 0,
                       "error_code": None, "_t0": time.monotonic(), "cancel": False})
        return True


def finish(error_code: str | None = None) -> None:
    with _lock:
        _state.update(running=False, cancel=False, finished_at=_now(), error_code=error_code)


def add(**counts: int) -> None:
    with _lock:
        for k, v in counts.items():
            _state[k] += v


def request_cancel() -> None:
    with _lock:
        _state["cancel"] = True


def cancelled() -> bool:
    with _lock:
        return bool(_state["cancel"])


def snapshot() -> dict:
    with _lock:
        s = {k: v for k, v in _state.items() if not k.startswith("_") and k != "cancel"}
        eta = None
        if _state["running"] and _state["_t0"] and _state["done"] and _state["todo"] > _state["done"]:
            rate = _state["done"] / max(time.monotonic() - _state["_t0"], 0.001)
            eta = int((_state["todo"] - _state["done"]) / rate)
        s["eta_s"] = eta
        return s
