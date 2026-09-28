"""Test-Fixtures für das OpenTor-Modul.

Die Tests nutzen eine In-Memory-DB. Trotzdem wird zuerst `_hh_isolation`
geladen: backend.service importiert hydrahive, und settings darf nie auf das
echte Datenverzeichnis zeigen (Vorfall 26.09.2026).
"""
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
