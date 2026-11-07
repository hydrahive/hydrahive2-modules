"""Gemeinsame Helfer der Workspace-Migration: Marker atomar speichern, Rechte der gezogenen Daten öffnen."""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path

from . import workspace_mount


def save(project_id: str, state: dict) -> None:
    marker = workspace_mount.marker(project_id)
    tmp = marker.with_suffix(".tmp")
    clean = {k: v for k, v in state.items() if not k.startswith("_")}
    tmp.write_text(json.dumps(clean, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, marker)


def open_group_bits(path: Path) -> None:
    """Pulldaten gehören dem Hostdienst; Gruppe schreibbar, Symlinks unangetastet."""
    for root, dirs, files in os.walk(path, followlinks=False):
        root_path = Path(root)
        os.chmod(root_path, stat.S_IMODE(root_path.stat().st_mode) | 0o030)
        for name in dirs:
            child = root_path / name
            if not child.is_symlink():
                os.chmod(child, stat.S_IMODE(child.stat().st_mode) | 0o030)
        for name in files:
            child = root_path / name
            if not child.is_symlink():
                os.chmod(child, stat.S_IMODE(child.stat().st_mode) | 0o020)
