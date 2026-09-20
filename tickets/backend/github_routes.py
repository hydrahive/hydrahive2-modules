"""Project-scoped, read-only GitHub Projects API."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status

from hydrahive.api.middleware.auth import AuthPrincipal, require_principal
from hydrahive.api.middleware.errors import coded
from hydrahive.projects.config import get as get_project
from hydrahive.api.routes._project_route_helpers import check_project_access

from . import github, github_provider

router = APIRouter(prefix="/github", tags=["ticket-github"])
Auth = Annotated[AuthPrincipal, Depends(require_principal)]


def _connection(connection_id: str) -> dict:
    from hydrahive.db.connection import db
    with db() as conn:
        row = conn.execute("SELECT * FROM module_ticket_github_connections WHERE id=?", (connection_id,)).fetchone()
    if row is None:
        raise coded(status.HTTP_404_NOT_FOUND, "github_connection_not_found")
    return dict(row)


def _access(project_id: str, auth: AuthPrincipal, required: str = "read") -> None:
    project = get_project(project_id)
    if project is None:
        raise coded(status.HTTP_404_NOT_FOUND, "project_not_found")
    check_project_access(project, auth.username, auth.role, required)


def _provider_error(exc: github_provider.GitHubProviderError):
    raise coded(exc.status, exc.code)


@router.post("/discovery")
def discovery_route(auth: Auth, body: github.GitHubDiscoveryRequest) -> dict:
    _access(body.project_id, auth)
    try:
        if body.owner:
            return {"owners": [], "repositories": github_provider.list_repositories(auth.username, body.credential_name, body.owner)}
        return {"owners": github_provider.discover_owners(auth.username, body.credential_name), "repositories": []}
    except github_provider.GitHubProviderError as exc:
        return _provider_error(exc)


@router.post("/connections", status_code=status.HTTP_201_CREATED)
def create_connection_route(auth: Auth, body: github.GitHubConnectionCreate) -> dict:
    _access(body.project_id, auth, "write")
    try:
        return github.create_connection(body, auth)
    except ValueError as exc:
        raise coded(status.HTTP_409_CONFLICT, str(exc))


@router.get("/connections/{project_id}")
def list_connections_route(auth: Auth, project_id: str) -> list[dict]:
    _access(project_id, auth)
    return github.list_connections(project_id)


@router.patch("/connections/{connection_id}")
def update_connection_route(auth: Auth, connection_id: str, body: github.GitHubConnectionUpdate) -> dict:
    connection = _connection(connection_id)
    _access(connection["project_id"], auth, "write")
    updated = github.update_connection(connection_id, body.sync_mode, auth)
    if updated is None:
        raise coded(status.HTTP_404_NOT_FOUND, "github_connection_not_found")
    return updated


@router.get("/connections/{connection_id}/check")
def check_connection_route(auth: Auth, connection_id: str) -> dict:
    connection = _connection(connection_id)
    _access(connection["project_id"], auth)
    try:
        return github_provider.connection_check(connection["created_by"], connection["credential_name"], connection["project_id"])
    except github_provider.GitHubProviderError as exc:
        return _provider_error(exc)


@router.get("/connections/{connection_id}/projects")
def projects_route(auth: Auth, connection_id: str) -> list[dict]:
    connection = _connection(connection_id)
    _access(connection["project_id"], auth)
    try:
        return github_provider.list_projects(
            connection["created_by"], connection["credential_name"], connection["owner"], connection["project_id"]
        )
    except github_provider.GitHubProviderError as exc:
        return _provider_error(exc)


@router.get("/connections/{connection_id}/items")
def project_items_route(
    auth: Auth, connection_id: str,
    number: Annotated[int, Path(ge=1)],
) -> list[dict]:
    connection = _connection(connection_id)
    _access(connection["project_id"], auth)
    try:
        return github_provider.list_project_items(
            connection["created_by"], connection["credential_name"], connection["owner"], number, connection["project_id"]
        )
    except github_provider.GitHubProviderError as exc:
        return _provider_error(exc)


def _require_push(connection: dict, auth: AuthPrincipal) -> None:
    _access(connection["project_id"], auth, "write")
    if connection["sync_mode"] not in {"push", "bidirectional"}:
        raise coded(status.HTTP_409_CONFLICT, "github_write_disabled")


@router.patch("/connections/{connection_id}/project-field")
def project_field_route(auth: Auth, connection_id: str, body: github.GitHubProjectFieldUpdate) -> dict:
    connection = _connection(connection_id)
    _require_push(connection, auth)
    try:
        return github_provider.update_project_item_field(
            connection["created_by"], connection["credential_name"], body.project_id, body.item_id, body.field_id,
            body.option_id, connection["repository"], connection["project_id"],
        )
    except github_provider.GitHubProviderError as exc:
        return _provider_error(exc)


@router.post("/connections/{connection_id}/project-items")
def add_project_item_route(auth: Auth, connection_id: str, body: github.GitHubProjectItemMutation) -> dict:
    connection = _connection(connection_id)
    _require_push(connection, auth)
    if not body.content_id:
        raise coded(status.HTTP_422_UNPROCESSABLE_ENTITY, "github_content_id_required")
    try:
        return github_provider.add_project_item(
            connection["created_by"], connection["credential_name"], body.project_id, body.content_id,
            connection["repository"], connection["project_id"],
        )
    except github_provider.GitHubProviderError as exc:
        return _provider_error(exc)


@router.post("/connections/{connection_id}/project-items/remove")
def remove_project_item_route(auth: Auth, connection_id: str, body: github.GitHubProjectItemMutation) -> dict:
    connection = _connection(connection_id)
    _require_push(connection, auth)
    if not body.item_id:
        raise coded(status.HTTP_422_UNPROCESSABLE_ENTITY, "github_item_id_required")
    try:
        return github_provider.delete_project_item(
            connection["created_by"], connection["credential_name"], body.project_id, body.item_id,
            connection["repository"], connection["project_id"],
        )
    except github_provider.GitHubProviderError as exc:
        return _provider_error(exc)


@router.get("/connections/{connection_id}/tickets")
def linked_tickets_route(auth: Auth, connection_id: str) -> list[dict]:
    connection = _connection(connection_id)
    _access(connection["project_id"], auth)
    return github.list_linked_tickets(connection_id)


@router.post("/connections/{connection_id}/sync")
def sync_connection_route(auth: Auth, connection_id: str, body: github.GitHubSyncRequest) -> dict:
    connection = _connection(connection_id)
    _access(connection["project_id"], auth, "write")
    try:
        issues = github_provider.list_issues(
            connection["created_by"], connection["credential_name"], connection["owner"], connection["repository"], body.state, connection["project_id"]
        )[:body.limit]
        imported = [github.sync_issue_snapshot(connection, issue, auth) for issue in issues]
        return {"connection_id": connection_id, "state": body.state, "count": len(imported), "created": sum(1 for item in imported if item["created"]), "tickets": imported}
    except github_provider.GitHubProviderError as exc:
        return _provider_error(exc)
    except ValueError as exc:
        code = str(exc)
        if code.endswith("forbidden"):
            raise coded(status.HTTP_403_FORBIDDEN, code)
        raise coded(status.HTTP_409_CONFLICT, code)


@router.get("/connections/{connection_id}/issues")
def assigned_issues_route(auth: Auth, connection_id: str, assigned: bool = True, state: str = "open") -> list[dict]:
    connection = _connection(connection_id)
    _access(connection["project_id"], auth)
    try:
        if assigned:
            return github_provider.list_assigned_issues(
                connection["created_by"], connection["credential_name"], connection["owner"], connection["repository"], connection["project_id"]
            )
        return github_provider.list_issues(
            connection["created_by"], connection["credential_name"], connection["owner"], connection["repository"], state, connection["project_id"]
        )
    except github_provider.GitHubProviderError as exc:
        return _provider_error(exc)


@router.get("/issues/{owner}/{repository}/{number}")
def issue_route(auth: Auth, owner: str, repository: str, number: Annotated[int, Path(ge=1)]) -> dict:
    # Issue reads are only reachable through a configured project connection.
    from hydrahive.db.connection import db
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM module_ticket_github_connections WHERE owner=? AND repository=? AND enabled=1 LIMIT 1",
            (owner, repository),
        ).fetchone()
    if row is None:
        raise coded(status.HTTP_404_NOT_FOUND, "github_connection_not_found")
    _access(row["project_id"], auth)
    try:
        return github_provider.get_issue(row["created_by"], row["credential_name"], owner, repository, number, row["project_id"])
    except github_provider.GitHubProviderError as exc:
        return _provider_error(exc)


@router.post("/links", status_code=status.HTTP_201_CREATED)
def link_route(auth: Auth, body: github.GitHubLinkCreate) -> dict:
    try:
        return github.link_ticket(github.validate_remote_link(body), auth)
    except ValueError as exc:
        code = str(exc)
        status_code = status.HTTP_403_FORBIDDEN if code == "ticket_update_forbidden" else status.HTTP_409_CONFLICT
        if code.endswith("not_found"):
            status_code = status.HTTP_404_NOT_FOUND
        raise coded(status_code, code)


@router.delete("/links/{ticket_id}")
def unlink_route(auth: Auth, ticket_id: str) -> dict:
    try:
        return {"unlinked": True, "link": github.unlink_ticket(ticket_id, auth)}
    except ValueError as exc:
        code = str(exc)
        status_code = status.HTTP_403_FORBIDDEN if code == "ticket_update_forbidden" else status.HTTP_404_NOT_FOUND
        raise coded(status_code, code)


@router.get("/links/{ticket_id}")
def get_link_route(auth: Auth, ticket_id: str) -> dict:
    del auth
    result = github.get_link(ticket_id)
    if result is None:
        raise coded(status.HTTP_404_NOT_FOUND, "github_link_not_found")
    return result


@router.get("/connections")
def list_connections_query_route(auth: Auth, project_id: str) -> list[dict]:
    _access(project_id, auth)
    return github.list_connections(project_id)


@router.delete("/connections/{connection_id}")
def disable_connection_route(auth: Auth, connection_id: str) -> dict:
    connection = _connection(connection_id)
    _access(connection["project_id"], auth, "write")
    from hydrahive.db.connection import db
    with db(immediate=True) as conn:
        conn.execute("UPDATE module_ticket_github_connections SET enabled=0, updated_at=strftime('%Y-%m-%dT%H:%M:%SZ', 'now') WHERE id=?", (connection_id,))
    return {"disabled": True, "connection_id": connection_id}


@router.post("/connections/{connection_id}/check")
def check_connection_post_route(auth: Auth, connection_id: str) -> dict:
    return check_connection_route(auth, connection_id)


@router.get("/projects")
def projects_query_route(auth: Auth, connection_id: str) -> list[dict]:
    return projects_route(auth, connection_id)


@router.get("/projects/{project_id}/items")
def project_items_spec_route(
    auth: Auth, project_id: str, connection_id: str, number: Annotated[int | None, Query(ge=1)] = None,
) -> list[dict]:
    selected_number = number
    if selected_number is None:
        try:
            selected_number = int(project_id)
        except ValueError:
            raise coded(status.HTTP_400_BAD_REQUEST, "github_project_number_required")
    return project_items_route(auth, connection_id, selected_number)


@router.patch("/tickets/{ticket_id}/github")
def ticket_github_update_route(auth: Auth, ticket_id: str, body: github.GitHubIssueUpdate) -> dict:
    link = github.get_link(ticket_id)
    if link is None:
        raise coded(status.HTTP_404_NOT_FOUND, "github_link_not_found")
    connection = _connection(link["connection_id"])
    _access(connection["project_id"], auth, "write")
    if connection["sync_mode"] not in {"push", "bidirectional"}:
        raise coded(status.HTTP_409_CONFLICT, "github_write_disabled")
    if not link["issue_node_id"]:
        raise coded(status.HTTP_409_CONFLICT, "github_issue_node_id_missing")
    try:
        issue = github_provider.update_issue(
            connection["created_by"], connection["credential_name"], connection["owner"], connection["repository"],
            link["issue_node_id"], title=body.title, body=body.body, state=body.state, project_id=connection["project_id"],
        )
        return github.sync_issue_snapshot(connection, issue, auth)
    except github_provider.GitHubProviderError as exc:
        return _provider_error(exc)


@router.get("/tickets/{ticket_id}/github")
def ticket_github_route(auth: Auth, ticket_id: str) -> dict:
    del auth
    result = github.get_link(ticket_id)
    if result is None:
        raise coded(status.HTTP_404_NOT_FOUND, "github_link_not_found")
    return result


@router.post("/tickets/{ticket_id}/github/link", status_code=status.HTTP_201_CREATED)
def ticket_github_link_route(auth: Auth, ticket_id: str, body: github.GitHubLinkCreate) -> dict:
    if body.ticket_id != ticket_id:
        raise coded(status.HTTP_400_BAD_REQUEST, "ticket_id_mismatch")
    return link_route(auth, body)


@router.delete("/tickets/{ticket_id}/github/link")
def ticket_github_unlink_route(auth: Auth, ticket_id: str) -> dict:
    return unlink_route(auth, ticket_id)
