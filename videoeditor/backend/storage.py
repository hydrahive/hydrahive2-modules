"""Video-Editor — Datei-Ablage im Projekt-Workspace.

Alles liegt projektgebunden unter ``<projekt-workspace>/videoeditor/``:

    originals/<file-id>.<ext>   hochgeladenes Original
    proxies/<file-id>.mp4       480p-Proxy zum Scrubben
    sprites/<file-id>.jpg       Filmstrip-Thumbnail-Sprite
    meta/<file-id>.json         Probe-Ergebnis + Keyframes + EDL
    exports/<export-id>.mp4     gerenderte Exports

Der Workspace-Root kommt aus ``ensure_workspace(project_id)`` (Core), analog
zum Atelier-Modul. Alle Pfade werden gegen den videoeditor-Root validiert
(resolve()+relative_to) — kein Path-Traversal möglich.
"""
from __future__ import annotations

import re
import uuid
from pathlib import Path

from hydrahive.projects._config_io import list_for_user
from hydrahive.projects._paths import ensure_workspace

_PROJECT_ID_RE = re.compile(r"^[A-Za-z0-9-]{8,64}$")
_ID_RE = re.compile(r"^[a-f0-9]{32}$")

MAX_UPLOAD_BYTES = 4 * 1024 * 1024 * 1024  # 4 GiB pro Video
_ALLOWED_VIDEO_EXT = {"mp4", "mov", "mkv", "webm", "avi"}


def is_project_id(project_id: str) -> bool:
    return bool(_PROJECT_ID_RE.match(project_id))


def user_can_access(user: str, project_id: str) -> bool:
    return any(p["id"] == project_id for p in list_for_user(user))


def new_id() -> str:
    return uuid.uuid4().hex


def is_valid_id(file_id: str) -> bool:
    return bool(_ID_RE.match(file_id))


def video_ext_from(filename: str) -> str | None:
    ext = (filename.rsplit(".", 1)[-1] if "." in filename else "").lower()
    return ext if ext in _ALLOWED_VIDEO_EXT else None


def _root(project_id: str) -> Path:
    root = ensure_workspace(project_id) / "videoeditor"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _subdir(project_id: str, name: str) -> Path:
    d = _root(project_id) / name
    d.mkdir(parents=True, exist_ok=True)
    return d


def _safe_path(project_id: str, subdir: str, filename: str) -> Path:
    """Baut einen Pfad unter <root>/<subdir>/<filename> und validiert, dass er
    innerhalb des videoeditor-Roots bleibt (Traversal-Schutz)."""
    root = _root(project_id).resolve()
    p = (_subdir(project_id, subdir) / filename).resolve()
    p.relative_to(root)  # wirft ValueError bei Traversal
    return p


def original_path(project_id: str, file_id: str, ext: str) -> Path:
    return _safe_path(project_id, "originals", f"{file_id}.{ext}")


def proxy_path(project_id: str, file_id: str) -> Path:
    return _safe_path(project_id, "proxies", f"{file_id}.mp4")


def sprite_path(project_id: str, file_id: str) -> Path:
    return _safe_path(project_id, "sprites", f"{file_id}.jpg")


def meta_path(project_id: str, file_id: str) -> Path:
    return _safe_path(project_id, "meta", f"{file_id}.json")


def export_path(project_id: str, export_id: str) -> Path:
    return _safe_path(project_id, "exports", f"{export_id}.mp4")


def list_originals(project_id: str) -> list[Path]:
    d = _subdir(project_id, "originals")
    return sorted(d.glob("*.*"))


def jobs_dir(project_id: str) -> Path:
    return _subdir(project_id, "jobs")
