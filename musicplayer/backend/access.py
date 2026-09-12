"""Projekt-RBAC und aktuelle Principal-Auflösung für Musicplayer-Routen."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Literal

from fastapi import Depends, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from hydrahive.api.middleware.auth import AuthPrincipal, _decode
from hydrahive.api.middleware.errors import coded
from hydrahive.api.middleware.users import get_by_id
from hydrahive.projects import _members_model as members_model
from hydrahive.projects import config as project_config

ProjectRole = Literal["read", "write", "admin"]
_stream_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True, slots=True)
class ProjectAccess:
    role: ProjectRole

    @property
    def can_upload(self) -> bool:
        return members_model.has_at_least(self.role, "write")

    @property
    def can_delete(self) -> bool:
        return members_model.has_at_least(self.role, "admin")


def require_project_access(
    project_id: str,
    principal: AuthPrincipal,
    minimum: ProjectRole = "read",
) -> ProjectAccess:
    try:
        project = project_config.get(project_id)
    except FileNotFoundError as exc:
        raise coded(status.HTTP_404_NOT_FOUND, "project_not_found") from exc

    if principal.role == "admin":
        role: ProjectRole = "admin"
    else:
        resolved = members_model.role_of(project, principal.username)
        if resolved is None:
            raise coded(status.HTTP_403_FORBIDDEN, "project_access_denied")
        role = resolved

    if not members_model.has_at_least(role, minimum):
        raise coded(status.HTTP_403_FORBIDDEN, "project_access_denied")
    return ProjectAccess(role=role)


def _credential_principal(credential: dict) -> AuthPrincipal:
    user_id = credential.get("uid", credential.get("user_id"))
    if not isinstance(user_id, str) or not user_id:
        raise coded(status.HTTP_401_UNAUTHORIZED, "invalid_token")
    current = get_by_id(user_id)
    username = credential.get("sub", credential.get("username"))
    if not current or current["username"] != username:
        raise coded(status.HTTP_401_UNAUTHORIZED, "invalid_token")
    return AuthPrincipal(
        user_id=current["user_id"],
        username=current["username"],
        role=current["role"],
    )


def stream_principal(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_stream_bearer)],
    token: Annotated[str | None, Query()] = None,
) -> AuthPrincipal:
    """Authentifiziert Audio-Tags per Header oder Query-JWT gegen den User-Store."""
    raw = credentials.credentials if credentials else token
    if not raw:
        raise coded(status.HTTP_401_UNAUTHORIZED, "not_authenticated")
    if raw.startswith("hhk_"):
        from hydrahive.api.middleware.api_keys import verify as verify_key

        credential = verify_key(raw)
        if not credential:
            raise coded(status.HTTP_401_UNAUTHORIZED, "invalid_token")
    else:
        credential = _decode(raw)
    return _credential_principal(credential)
