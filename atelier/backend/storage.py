"""Atelier — Datei-Ablage im Projekt-Workspace.

Alles was im Atelier entsteht, liegt projektgebunden unter
``<projekt-workspace>/atelier/``:

    characters/<char-id>/   Hero-Referenzbilder + character.json
    output/                 generierte Bilder + <name>.json (Sidecar)
    ci.json                 CI-Kit des Projekts

Der Workspace-Root kommt aus ``ensure_workspace(project_id)`` (Core). Zugriff
ist auf Projekt-Mitglieder beschränkt (``user_can_access``). Alle Pfade werden
gegen den Atelier-Root validiert (resolve()+relative_to) → kein Traversal.
"""
from __future__ import annotations

import re
import uuid
from pathlib import Path

from hydrahive.projects._config_io import list_for_user
from hydrahive.projects._paths import ensure_workspace

_ID_RE = re.compile(r"^[a-f0-9]{32}$")
_PROJECT_ID_RE = re.compile(r"^[A-Za-z0-9-]{8,64}$")


def is_project_id(value: str) -> bool:
    """Grobe Form-Prüfung für Projekt-IDs (UUID-artig, mit Bindestrichen)."""
    return bool(_PROJECT_ID_RE.match(value or ""))


def user_can_access(username: str, project_id: str) -> bool:
    """True, wenn der User Mitglied/Ersteller des Projekts ist."""
    return any(p.get("id") == project_id for p in list_for_user(username))


def atelier_root(project_id: str) -> Path:
    """``<projekt-workspace>/atelier`` — angelegt falls nötig."""
    root = (ensure_workspace(project_id) / "atelier").resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def characters_dir(project_id: str) -> Path:
    d = atelier_root(project_id) / "characters"
    d.mkdir(parents=True, exist_ok=True)
    return d


def output_dir(project_id: str) -> Path:
    d = atelier_root(project_id) / "output"
    d.mkdir(parents=True, exist_ok=True)
    return d


def new_id() -> str:
    """Frische 32-stellige Hex-ID (für Charaktere/Outputs)."""
    return uuid.uuid4().hex


def is_valid_id(value: str) -> bool:
    return bool(_ID_RE.match(value or ""))


def safe_under(root: Path, rel: str) -> Path | None:
    """Validiert ``rel`` gegen ``root``. Absoluter Pfad oder None bei Ausbruch."""
    if not rel or rel.startswith("/"):
        return None
    candidate = (root / rel).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return None
    return candidate


def save_image_bytes(project_id: str, raw: bytes, *, ext: str = "png") -> str:
    """Schreibt Bytes nach output/ unter UUID-Namen. Gibt den Dateinamen zurück."""
    name = f"{new_id()}.{ext.lstrip('.').lower()}"
    (output_dir(project_id) / name).write_bytes(raw)
    return name


def save_reference_bytes(project_id: str, char_id: str, raw: bytes, *, ext: str = "png") -> str:
    """Schreibt ein Referenzbild in den Charakter-Ordner. Gibt relativen Pfad zurück."""
    cdir = characters_dir(project_id) / char_id
    cdir.mkdir(parents=True, exist_ok=True)
    name = f"{new_id()}.{ext.lstrip('.').lower()}"
    (cdir / name).write_bytes(raw)
    return f"characters/{char_id}/{name}"
