"""Sichere, vom Nutzerpfad unabhängige Fallverzeichnisse."""
from __future__ import annotations

import re
from pathlib import Path

from hydrahive.settings import settings

CASE_ID = re.compile(r"^[A-Za-z0-9-]{8,64}$")
PROJECT_ID = re.compile(r"^[A-Za-z0-9-]{8,64}$")


def check_case_id(case_id: str) -> str:
    """Nur IDs aus festem Zeichenvorrat; Pfade sind nie API-Eingabe."""
    if not CASE_ID.fullmatch(case_id or ""):
        raise ValueError("invalid case id")
    return case_id


def check_project_id(project_id: str) -> str:
    if not PROJECT_ID.fullmatch(project_id or ""):
        raise ValueError("invalid project id")
    return project_id


def cases_root(case_id: str) -> Path:
    """Wurzelverzeichnis eines Falls unterhalb des Modul-Datenordners."""
    check_case_id(case_id)
    return settings.data_dir / "modules" / "zerlegewerkstatt" / "cases" / case_id
