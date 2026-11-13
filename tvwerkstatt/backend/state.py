"""Zustand der TV-Werkstatt: Geräte und Bauten (Tabellen module_tvwerkstatt_*)."""
from __future__ import annotations

from hydrahive.db.connection import db

_DEVICE_PUBLIC = ("device_id", "name", "address", "adb_port", "kind", "model", "android", "sdk", "build",
                  "stock_home", "current_home", "live_tv", "adb_state", "checked_at", "created_at")
_BUILD_PUBLIC = ("build_id", "part", "commit_id", "sha256", "package", "version", "size", "signer", "state",
                 "log_tail", "created_at")


def devices() -> list[dict]:
    """Alle Geräte, nur Felder, die die Oberfläche braucht (wer es eingetragen hat, bleibt intern)."""
    with db() as conn:
        rows = conn.execute(f"SELECT {', '.join(_DEVICE_PUBLIC)} FROM module_tvwerkstatt_devices "
                            "ORDER BY created_at, device_id").fetchall()
    return [dict(zip(_DEVICE_PUBLIC, r, strict=True)) for r in rows]


def builds(limit: int = 20) -> list[dict]:
    with db() as conn:
        rows = conn.execute(f"SELECT {', '.join(_BUILD_PUBLIC)} FROM module_tvwerkstatt_builds "
                            "ORDER BY created_at DESC, build_id LIMIT ?", (limit,)).fetchall()
    return [dict(zip(_BUILD_PUBLIC, r, strict=True)) for r in rows]


def device_targets() -> list[tuple[str, int]]:
    """Adresse und ADB-Port aller eingetragenen Fernseher – daraus entstehen die Ausnahmen der Sperrliste."""
    with db() as conn:
        rows = conn.execute("SELECT address, adb_port FROM module_tvwerkstatt_devices ORDER BY address").fetchall()
    return [(str(a), int(p)) for a, p in rows]
