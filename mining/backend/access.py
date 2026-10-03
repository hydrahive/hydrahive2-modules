"""Freigabe mining.control für steuernde Routen (Core: docs/specs/access-groups.md).

Mit Freigaben-System prüft require_capability. Ohne (älterer Core) reicht es
nicht, angemeldet zu sein: Steuern bleibt dann Admins vorbehalten.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from hydrahive.api.middleware.auth import require_admin

try:
    from hydrahive.access.deps import require_capability
except ImportError:  # Core ohne Freigaben-System
    require_capability = None

CONTROL = "mining.control"

if require_capability is not None:
    Control = Annotated[object, Depends(require_capability(CONTROL))]
else:
    Control = Annotated[tuple[str, str], Depends(require_admin)]
