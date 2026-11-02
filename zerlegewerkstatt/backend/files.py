"""Sichere, vom Nutzerpfad unabhängige Fallverzeichnisse."""
from __future__ import annotations

import re
from pathlib import Path

from hydrahive.settings import settings

_CASE_ID = re.compile(r"^[A-Za-z0-9-]{8,64}$")


def cases_root(case_id: str) -> Path:
    if not _CASE_ID.fullmatch(case_id or ""):
        raise ValueError("invalid case id")
    root = settings.data_dir / "modules" / "zerlegewerkstatt" / "cases" / case_id
    return root
