"""Validated, user- and team-scoped saved ticket views."""
from __future__ import annotations

import json
from uuid import uuid4

from hydrahive.api.middleware.auth import AuthPrincipal
from hydrahive.db.connection import db

from .models import SavedViewUpdate
from .permissions import can_manage_team, is_admin

_ALLOWED_FILTERS = {"status", "priority", "team_id", "assigned_to", "project_id", "query", "overdue", "unassigned"}
_ALLOWED_SORTS = {"updated_at", "due_at", "created_at", "priority", "number"}


def _now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _validate_filters(filters: dict) -> dict:
    if not isinstance(filters, dict) or any(key not in _ALLOWED_FILTERS for key in filters):
        raise ValueError("invalid_view_filter")
    return {str(key): value for key, value in filters.items()}


def _view(row) -> dict:
    result = dict(row)
    result["filters"] = json.loads(result.pop("filters_json", "{}"))
    return result


def create_view(
    principal: AuthPrincipal,
    *, name: str,
    filters: dict,
    sort: str = "updated_at",
    direction: str = "desc",
    team_id: str | None = None,
) -> dict:
    name = name.strip()
    if not name or len(name) > 100:
        raise ValueError("invalid_view_name")
    if sort not in _ALLOWED_SORTS or direction not in {"asc", "desc"}:
        raise ValueError("invalid_view_sort")
    if team_id and not (is_admin(principal) or _can_manage_team(team_id, principal)):
        raise PermissionError("saved_view_forbidden")
    view_id = str(uuid4())
    now = _now()
    with db(immediate=True) as conn:
        conn.execute(
            "INSERT INTO module_ticket_saved_views "
            "(id,owner_id,team_id,name,filters_json,sort,direction,created_at,updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (view_id, principal.user_id, team_id, name, json.dumps(_validate_filters(filters)), sort, direction, now, now),
        )
        row = conn.execute("SELECT * FROM module_ticket_saved_views WHERE id=?", (view_id,)).fetchone()
    return _view(row)


def _can_manage_team(team_id: str, principal: AuthPrincipal) -> bool:
    with db() as conn:
        return can_manage_team(conn, team_id, principal)


def list_views(principal: AuthPrincipal) -> list[dict]:
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM module_ticket_saved_views WHERE owner_id=? OR team_id IN "
            "(SELECT team_id FROM module_ticket_team_members WHERE user_id=?) "
            "ORDER BY updated_at DESC, name ASC",
            (principal.user_id, principal.user_id),
        ).fetchall()
    return [_view(row) for row in rows]


def update_view(view_id: str, body: SavedViewUpdate, principal: AuthPrincipal) -> dict:
    changes = body.model_dump(exclude_unset=True)
    if "name" in changes:
        changes["name"] = changes["name"].strip()
        if not changes["name"]:
            raise ValueError("invalid_view_name")
    if "filters" in changes:
        changes["filters"] = _validate_filters(changes["filters"])
    if "sort" in changes and changes["sort"] not in _ALLOWED_SORTS:
        raise ValueError("invalid_view_sort")
    if "direction" in changes and changes["direction"] not in {"asc", "desc"}:
        raise ValueError("invalid_view_sort")
    with db(immediate=True) as conn:
        row = conn.execute("SELECT * FROM module_ticket_saved_views WHERE id=?", (view_id,)).fetchone()
        if row is None:
            raise KeyError("saved_view_not_found")
        allowed = is_admin(principal) or row["owner_id"] == principal.user_id
        if row["team_id"]:
            allowed = allowed or can_manage_team(conn, row["team_id"], principal)
        if not allowed:
            raise PermissionError("saved_view_forbidden")
        assignments: list[str] = []
        args: list[object] = []
        for field in ("name", "sort", "direction"):
            if field in changes:
                assignments.append(f"{field}=?")
                args.append(changes[field])
        if "filters" in changes:
            assignments.append("filters_json=?")
            args.append(json.dumps(changes["filters"], ensure_ascii=False))
        assignments.append("updated_at=?")
        args.extend((_now(), view_id))
        if len(assignments) > 1:
            conn.execute(f"UPDATE module_ticket_saved_views SET {','.join(assignments)} WHERE id=?", args)
        updated = conn.execute("SELECT * FROM module_ticket_saved_views WHERE id=?", (view_id,)).fetchone()
    return _view(updated)


def delete_view(view_id: str, principal: AuthPrincipal) -> None:
    with db(immediate=True) as conn:
        row = conn.execute("SELECT * FROM module_ticket_saved_views WHERE id=?", (view_id,)).fetchone()
        if row is None:
            raise KeyError("saved_view_not_found")
        allowed = is_admin(principal) or row["owner_id"] == principal.user_id
        if row["team_id"]:
            allowed = allowed or can_manage_team(conn, row["team_id"], principal)
        if not allowed:
            raise PermissionError("saved_view_forbidden")
        conn.execute("DELETE FROM module_ticket_saved_views WHERE id=?", (view_id,))
