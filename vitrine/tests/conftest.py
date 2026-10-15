"""Test-Fixtures für Vitrine. `_hh_isolation` zuerst (Vorfall 26.09.2026), auch wenn die Renderer-Tests kein hydrahive brauchen."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _hh_isolation import (  # noqa: E402, F401 - pytest-Hooks, über conftest registriert
    pytest_collection_finish,
    pytest_configure,
    pytest_runtest_call,
    pytest_runtest_setup,
    pytest_unconfigure,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
