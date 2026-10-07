"""Storyteller — Dateigrundlagen: Projektordner, ID-Prüfung, Pfadschutz, atomares Schreiben."""
from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import tempfile
from pathlib import Path
from typing import Any

from hydrahive.projects import _members_model
from hydrahive.projects._config_io import get as get_project
from hydrahive.projects._paths import ensure_workspace

_ID_RE = re.compile(r"^[a-f0-9]{32}$")
_PROJECT_ID_RE = re.compile(r"^[A-Za-z0-9-]{8,64}$")


class StoryError(ValueError):
    """Ungültige Eingabe oder unbekanntes Objekt → HTTP 400/404."""

    def __init__(self, code: str, status: int = 400, detail: dict | None = None):
        super().__init__(code)
        self.code = code
        self.status = status
        self.detail = detail or {}   # Zusatzangaben für Oberfläche/Agent (z. B. vorhandene Steckbrief-ID)


def new_id() -> str:
    return secrets.token_hex(16)


def check_id(value: str, what: str = "id") -> str:
    if not isinstance(value, str) or not _ID_RE.match(value):
        raise StoryError(f"{what}_invalid", 404)
    return value


def is_project_id(value: str) -> bool:
    return bool(_PROJECT_ID_RE.match(value or ""))


def project_access(username: str, system_role: str, project_id: str, need: str) -> str:
    """Wie der Kern (check_project_access): System-Admin darf alles, sonst zählt die Projektrolle
    (read < write < admin). Ergebnis: "ok", "missing" (kein Projekt/kein Mitglied → 404) oder
    "read_only" (Mitglied, aber Rolle reicht nicht → 403)."""
    project = get_project(project_id) if is_project_id(project_id) else None
    if project is None:
        return "missing"
    if system_role == "admin":
        return "ok"
    role = _members_model.role_of(project, username)
    if role is None:
        return "missing"
    return "ok" if _members_model.has_at_least(role, need) else "read_only"


def story_root(project_id: str) -> Path:
    """``<projekt-workspace>/storyteller`` (wird erst beim Schreiben angelegt)."""
    if not is_project_id(project_id):
        raise StoryError("project_invalid", 404)
    return (ensure_workspace(project_id) / "storyteller").resolve()


def inside(base: Path, *parts: str) -> Path:
    """Pfad unter ``base`` – alles, was hinausführt, ist ein Fehler (kein Traversal)."""
    p = base.joinpath(*parts).resolve()
    try:
        p.relative_to(base.resolve())
    except ValueError as exc:
        raise StoryError("path_invalid", 404) from exc
    return p


FILE_MODE = 0o664  # wie die übrigen Workspace-Dateien (Dienst-umask 002); mkstemp allein gäbe 0600


def write_atomic(path: Path, data: str) -> None:
    """Temp-Datei im selben Ordner, dann ``os.replace``. Bei Fehler bleibt die alte Datei, kein Rest."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(data)
        os.chmod(tmp, FILE_MODE)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def write_json(path: Path, data: Any) -> None:
    write_atomic(path, json.dumps(data, ensure_ascii=False, indent=1) + "\n")


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise StoryError("not_found", 404) from exc


def scene_paths(d: Path, scene_id: str) -> tuple[Path, Path]:
    check_id(scene_id, "scene")
    return inside(d, "scenes", f"{scene_id}.json"), inside(d, "scenes", f"{scene_id}.md")


def text_sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_scene(d: Path, scene_id: str, meta: dict, text: str) -> None:
    """Text, dann Infos – zwei Dateien, also kein gemeinsamer atomarer Schritt. Die Infos tragen den Hash des
    Texts; passt er beim Lesen nicht (Absturz dazwischen), meldet get_scene das (siehe scenes.get_scene)."""
    meta_path, text_path = scene_paths(d, scene_id)
    write_atomic(text_path, text)
    write_json(meta_path, {**meta, "text_sha": text_sha(text)})
