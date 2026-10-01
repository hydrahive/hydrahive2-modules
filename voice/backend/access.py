"""Owner-/Admin-Zugriffsschutz für die einzelne lokale Voicebox."""
from __future__ import annotations

import os
from typing import Annotated

from fastapi import Depends, status
from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded

Auth = tuple[str, str]
Authenticated = Annotated[Auth, Depends(require_auth)]
_HEALTH_NOT_PROVIDED = object()


def _owner_name(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    owner = value.strip()
    return owner or None


async def _bridge_health() -> dict | None:
    # Laufzeit-Import vermeidet einen Zyklus beim Laden des Backend-Pakets.
    from . import _bridge_get

    return await _bridge_get("/health")


async def can_access_voice(
    auth: Auth,
    health: dict | None | object = _HEALTH_NOT_PROVIDED,
) -> bool:
    """Prüft Admin oder Besitzer; ENV hat Vorrang vor Bridge-/health.owner."""
    username, role = auth
    if role == "admin":
        return True

    owner = _owner_name(os.environ.get("VOICE_BRIDGE_OWNER"))
    if owner is None:
        if health is _HEALTH_NOT_PROVIDED:
            health = await _bridge_health()
        owner = _owner_name(health.get("owner")) if isinstance(health, dict) else None
    return owner is not None and username == owner


async def require_voice_owner(auth: Authenticated) -> Auth:
    """Erlaubt nur Admins oder dem bekannten Besitzer Zugriff auf die Box."""
    if not await can_access_voice(auth):
        raise coded(status.HTTP_403_FORBIDDEN, "voice_owner_required")
    return auth
