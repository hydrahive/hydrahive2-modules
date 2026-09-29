"""Freigabe homeassistant.control für die Schalt-Route (Core: docs/specs/access-groups.md).

Mit neuem Core prüft require_capability die Freigabe. Mit einem Core ohne
Freigaben-System (vor HydraHive-Core mit hydrahive.access) bleibt es beim
bisherigen Verhalten: angemeldet reicht. So läuft das Modul auf beiden Ständen.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from hydrahive.api.middleware.auth import require_auth

try:
    from hydrahive.access.deps import require_capability
except ImportError:  # Core ohne Freigaben-System
    require_capability = None

CONTROL = "homeassistant.control"

if require_capability is not None:
    Control = Annotated[object, Depends(require_capability(CONTROL))]
else:
    Control = Annotated[tuple[str, str], Depends(require_auth)]
