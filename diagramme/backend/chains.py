"""Ketten von Fassungen (Spec §12.6): Papierkorb und endgültiges Löschen gelten immer für die ganze Kette.

Eine Kette = erste Fassung (`version_of` zeigt immer auf sie) plus alle späteren Fassungen.
"""
from __future__ import annotations

import shutil
from typing import Any

from hydrahive.db.connection import db

from . import store


def chain_id(view_id: str) -> str:
    row = store.get(view_id)
    return (row["version_of"] or row["id"]) if row else view_id


def _ids(view_id: str) -> list[str]:
    return [v["id"] for v in store.versions(view_id)]


def trash_chain(view_id: str) -> None:
    for vid in _ids(view_id):
        store.trash(vid)


def restore_chain(view_id: str) -> None:
    for vid in _ids(view_id):
        store.restore(vid)


def purge_chain(view_id: str) -> None:
    """Endgültig: Zeilen und Ordner der ganzen Kette – nur innerhalb von data_dir/diagramme."""
    root = store.root().resolve()
    for vid in _ids(view_id):
        if not store.ID_RE.match(vid):
            continue
        folder = (root / vid).resolve()
        if folder.parent == root and folder.is_dir():
            shutil.rmtree(folder)
        with db() as c:
            c.execute("DELETE FROM module_diagrams WHERE id = ?", (vid,))


def can_change(row: dict[str, Any] | None, username: str, role: str) -> bool:
    """Wegwerfen/Löschen: nur wer es erstellt hat, oder Admin. Projekt-Mitglieder dürfen nur sehen."""
    return bool(row) and (role == "admin" or row["username"] == username)


def newest_per_chain(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Aus einer Liste (neueste zuerst) je Kette die neueste Fassung, mit Anzahl der Fassungen."""
    seen: dict[str, dict[str, Any]] = {}
    count: dict[str, int] = {}
    for r in rows:
        key = r["version_of"] or r["id"]
        count[key] = count.get(key, 0) + 1
        seen.setdefault(key, r)
    return [dict(r, versions=count[k]) for k, r in seen.items()]
