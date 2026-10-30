"""Zustand des Labors (PLAN-L1.md „Assistent“): eine Zeile je Server (id = 1).

`made` merkt, was das Modul WIRKLICH angelegt hat – „Labor entfernen“ löscht nur das. `running` = laufender Auftrag
(create/reset/test/probe/remove); höchstens einer gleichzeitig. Nach einem Neustart des Servers gilt ein offener
Auftrag als unterbrochen.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime

from hydrahive.db.connection import db

STEPS = ("start", "ready")
PARTS = ("network", "container", "setup", "snapshot", "project")
_T = "module_hydralabor_state"
_COLS = ("step", "running", "progress", "error_code", "error_step", "model", "cpu", "ram_mb", "disk_gb", "made",
         "last_net_ok", "last_test", "updated_at")


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ensure(conn) -> None:
    conn.execute(f"INSERT OR IGNORE INTO {_T} (id) VALUES (1)")


def get() -> dict:
    with db() as conn:
        _ensure(conn)
        conn.commit()
        row = conn.execute(f"SELECT {', '.join(_COLS)} FROM {_T} WHERE id = 1").fetchone()
    out = dict(zip(_COLS, row, strict=True))
    out["made"] = json.loads(out["made"] or "{}")
    out["last_test"] = json.loads(out["last_test"] or "{}")
    return out


def _set(**fields) -> None:
    fields["updated_at"] = _now()
    with db() as conn:
        _ensure(conn)
        conn.execute(f"UPDATE {_T} SET {', '.join(f'{k} = ?' for k in fields)} WHERE id = 1", tuple(fields.values()))
        conn.commit()


def clear() -> None:
    """Zeile des Moduls zurücksetzen (Labor entfernt). Nur die eigene Zeile (id = 1)."""
    with db() as conn:
        conn.execute(f"DELETE FROM {_T} WHERE id = 1")
        conn.commit()


def mark_made(part: str, **ids: str) -> None:
    if part not in PARTS:
        raise ValueError(part)
    made = get()["made"]
    made[part] = True
    made.update({k: v for k, v in ids.items() if k in ("project_id", "agent_id")})
    _set(made=json.dumps(made, sort_keys=True))


def unmark(*parts: str) -> None:
    made = get()["made"]
    for p in parts:
        made.pop(p, None)
        if p == "project":
            made.pop("project_id", None)
            made.pop("agent_id", None)
    _set(made=json.dumps(made, sort_keys=True))


def begin(job: str) -> bool:
    """Auftrag starten, wenn keiner läuft (atomar). Alter Fehler wird gelöscht."""
    with db() as conn:
        _ensure(conn)
        n = conn.execute(f"UPDATE {_T} SET running = ?, progress = '', error_code = '', error_step = '', "
                         "updated_at = ? WHERE id = 1 AND running = ''", (job, _now())).rowcount
        conn.commit()
    return n == 1


def progress(key: str) -> None:
    _set(progress=key)


def finish(*, error_code: str = "", error_step: str = "") -> None:
    _set(running="", progress="", error_code=error_code, error_step=error_step)


def save_choice(*, model: str, cpu: int, ram_mb: int, disk_gb: int) -> None:
    _set(model=model, cpu=cpu, ram_mb=ram_mb, disk_gb=disk_gb)


def set_step(step: str) -> None:
    if step not in STEPS:
        raise ValueError(step)
    _set(step=step)


def net_ok() -> None:
    _set(last_net_ok=_now())


def set_test(result: dict) -> None:
    _set(last_test=json.dumps({**result, "at": _now()}, sort_keys=True))


def recover_after_restart() -> None:
    """Beim Laden des Moduls: ein offener Auftrag lief im alten Prozess und ist weg."""
    if get()["running"]:
        finish(error_code="labor_interrupted")
