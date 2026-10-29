"""Freigabe fernseher.control für die Schalt-Routen (wie homeassistant/backend/access.py).

Mit Freigaben-System prüft require_capability; mit einem älteren Core reicht Admin (sicherer Rückfall –
Schalten soll ohne Freigaben-System nicht für alle offen sein).
"""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from hydrahive.api.middleware.auth import require_admin

try:
    from hydrahive.access.deps import require_capability
except ImportError:  # Core ohne Freigaben-System
    require_capability = None

CONTROL = "fernseher.control"

if require_capability is not None:
    Control = Annotated[object, Depends(require_capability(CONTROL))]
else:
    Control = Annotated[tuple[str, str], Depends(require_admin)]
