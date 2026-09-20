"""Least-privilege GitHub agent tools: read operations and explicit link writes."""
from __future__ import annotations

from pydantic import ValidationError
from hydrahive.tools.base import Tool, ToolContext, ToolResult

from .. import github, github_provider
from .context import invalid_principal, invalid_request, principal_for, service_failure


def _read_schema(properties: dict, required: list[str]) -> dict:
    return {"type": "object", "additionalProperties": False, "properties": properties, "required": required}


async def _project_list(args: dict, ctx: ToolContext) -> ToolResult:
    principal = principal_for(ctx)
    if principal is None:
        return invalid_principal()
    try:
        connection = _connection_for_project(args["connection_id"], ctx.project_id)
        return ToolResult.ok({"projects": github_provider.list_projects(
            connection["created_by"], connection["credential_name"], connection["owner"]
        )})
    except github_provider.GitHubProviderError as exc:
        return ToolResult.fail(exc.code)
    except (KeyError, TypeError, ValueError):
        return invalid_request()
    except Exception as exc:
        return service_failure(exc)


async def _project_items(args: dict, ctx: ToolContext) -> ToolResult:
    principal = principal_for(ctx)
    if principal is None:
        return invalid_principal()
    try:
        connection_id = args["connection_id"]
        number = args["number"]
        if not isinstance(connection_id, str) or not isinstance(number, int) or number < 1:
            return invalid_request()
        connection = _connection_for_project(connection_id, ctx.project_id)
        return ToolResult.ok({"items": github_provider.list_project_items(
            connection["created_by"], connection["credential_name"], connection["owner"], number
        )})
    except github_provider.GitHubProviderError as exc:
        return ToolResult.fail(exc.code)
    except (KeyError, TypeError, ValueError):
        return invalid_request()
    except Exception as exc:
        return service_failure(exc)


async def _issue(args: dict, ctx: ToolContext) -> ToolResult:
    principal = principal_for(ctx)
    if principal is None:
        return invalid_principal()
    try:
        owner, repository, number = args["owner"], args["repository"], args["number"]
        if not isinstance(owner, str) or not isinstance(repository, str) or not isinstance(number, int) or number < 1:
            return invalid_request()
        connection = _connection_for_repo(owner, repository, ctx.project_id)
        return ToolResult.ok(github_provider.get_issue(
            connection["created_by"], connection["credential_name"], owner, repository, number
        ))
    except github_provider.GitHubProviderError as exc:
        return ToolResult.fail(exc.code)
    except (KeyError, TypeError, ValueError):
        return invalid_request()
    except Exception as exc:
        return service_failure(exc)


def _connection_for_project(connection_id: str, project_id: str | None) -> dict:
    if not project_id:
        raise ValueError("github_project_required")
    from hydrahive.db.connection import db
    with db() as conn:
        row = conn.execute("SELECT * FROM module_ticket_github_connections WHERE id=? AND enabled=1", (connection_id,)).fetchone()
    if row is None or (project_id is not None and row["project_id"] != project_id):
        raise ValueError("github_connection_not_found")
    return dict(row)


def _connection_for_repo(owner: str, repository: str, project_id: str | None) -> dict:
    if not project_id:
        raise ValueError("github_project_required")
    from hydrahive.db.connection import db
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM module_ticket_github_connections WHERE owner=? AND repository=? AND enabled=1 LIMIT 1",
            (owner, repository),
        ).fetchone()
    if row is None or (project_id is not None and row["project_id"] != project_id):
        raise ValueError("github_connection_not_found")
    return dict(row)


async def _ticket_read(args: dict, ctx: ToolContext) -> ToolResult:
    if principal_for(ctx) is None:
        return invalid_principal()
    ticket_id = args.get("ticket_id")
    if not isinstance(ticket_id, str) or not ticket_id:
        return invalid_request()
    result = github.get_link(ticket_id)
    if result is None:
        return ToolResult.fail("github_link_not_found")
    return ToolResult.ok(result)


async def _link(args: dict, ctx: ToolContext) -> ToolResult:
    principal = principal_for(ctx)
    if principal is None:
        return invalid_principal()
    try:
        body = github.GitHubLinkCreate.model_validate(args)
        result = github.link_ticket(github.validate_remote_link(body), principal, actor_id=ctx.agent_id)
        return ToolResult.ok({"linked": True, "link": result})
    except ValidationError:
        return invalid_request()
    except ValueError as exc:
        return ToolResult.fail(str(exc))
    except Exception as exc:
        return service_failure(exc)


async def _unlink(args: dict, ctx: ToolContext) -> ToolResult:
    principal = principal_for(ctx)
    if principal is None:
        return invalid_principal()
    try:
        ticket_id = args["ticket_id"]
        if not isinstance(ticket_id, str):
            return invalid_request()
        result = github.unlink_ticket(ticket_id, principal, actor_id=ctx.agent_id)
        return ToolResult.ok({"unlinked": True, "link": result})
    except (KeyError, TypeError):
        return invalid_request()
    except ValueError as exc:
        return ToolResult.fail(str(exc))
    except Exception as exc:
        return service_failure(exc)


GITHUB_PROJECT_LIST_TOOL = Tool(
    "github_project_list", "Liest GitHub-Projects (read-only).",
    _read_schema({"connection_id": {"type": "string", "minLength": 1}}, ["connection_id"]),
    _project_list, category="integrations",
)
GITHUB_PROJECT_ITEMS_TOOL = Tool(
    "github_project_read", "Liest GitHub-Project-Items (read-only).",
    _read_schema({"connection_id": {"type": "string", "minLength": 1}, "number": {"type": "integer", "minimum": 1}}, ["connection_id", "number"]),
    _project_items, category="integrations",
)
GITHUB_ISSUE_TOOL = Tool(
    "ticket_github_read", "Liest die externe Ticket-Verknüpfung (read-only).",
    _read_schema({"ticket_id": {"type": "string", "minLength": 1}}, ["ticket_id"]),
    _ticket_read, category="integrations",
)
GITHUB_LINK_TOOL = Tool(
    "ticket_github_link", "Verknüpft ein Ticket mit einem GitHub-Issue.",
    _read_schema({"ticket_id": {"type": "string", "minLength": 1}, "connection_id": {"type": "string", "minLength": 1}, "owner": {"type": "string", "minLength": 1}, "repository": {"type": "string", "minLength": 1}, "issue_number": {"type": "integer", "minimum": 1}, "issue_url": {"type": "string", "pattern": "^https://github\\.com/"}}, ["ticket_id", "connection_id", "owner", "repository", "issue_number", "issue_url"]),
    _link, category="integrations",
)
GITHUB_UNLINK_TOOL = Tool(
    "ticket_github_unlink", "Löst die GitHub-Verknüpfung eines Tickets.",
    _read_schema({"ticket_id": {"type": "string", "minLength": 1}}, ["ticket_id"]),
    _unlink, category="integrations",
)
