"""Ablage des Studios unter <projekt>/studio/ (Spec „Bauplan Etappe 2“). Atomar schreiben, robust lesen."""
from __future__ import annotations

import json
import os
import re
import threading
import uuid
from pathlib import Path
from typing import Any

from hydrahive.projects._paths import ensure_workspace, workspace_path

_ID = re.compile(r"^[a-f0-9]{32}$")


def is_id(value: Any) -> bool:
    return isinstance(value, str) and bool(_ID.match(value))


def new_id() -> str:
    return uuid.uuid4().hex


def project_root(project_id: str) -> Path:
    return workspace_path(project_id)


def root(project_id: str, *, create: bool = False) -> Path:
    """<projekt>/studio – nur mit `create` wird der Ordner angelegt (Lesen legt nie etwas an)."""
    base = ensure_workspace(project_id) if create else workspace_path(project_id)
    d = base / "studio"
    if create:
        d.mkdir(parents=True, exist_ok=True)
    return d


def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def write_json(path: Path, data: Any) -> None:
    """Atomar schreiben. Eigene Temp-Datei je Aufruf: gleichzeitige Schreiber nehmen sich die Datei nicht weg."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{uuid.uuid4().hex[:12]}.tmp")
    try:
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


_locks: dict[str, threading.RLock] = {}
_locks_guard = threading.Lock()


def project_lock(project_id: str) -> threading.RLock:
    """Sperre je Projekt für Lesen-Ändern-Schreiben (Aufträge laufen in eigenen Threads). Wiedereintrittsfähig."""
    with _locks_guard:
        return _locks.setdefault(project_id, threading.RLock())


def safe_rel(project_id: str, rel: Any, exts: set[str]) -> str | None:
    """Pfad relativ zum Projekt, falls er auf eine echte Datei im Projekt zeigt (kein Symlink, passende Endung)."""
    if not isinstance(rel, str) or not rel or rel.startswith("/") or "\\" in rel:
        return None
    base = project_root(project_id)
    p = base / rel
    try:
        if p.is_symlink() or not p.is_file() or not p.resolve().is_relative_to(base.resolve()):
            return None
    except OSError:
        return None
    return rel if p.suffix.lower().lstrip(".") in exts else None
