"""Small, read-only GitHub GraphQL provider with strict network boundaries."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from hydrahive.credentials.store import get_credential
from hydrahive.projects import config as project_config

PROJECT_TOKEN_REF = "project_git_token"

GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"
_TIMEOUT = httpx.Timeout(10.0, connect=5.0)
_PAGE_SIZE = 50
_MAX_PAGES = 20


@dataclass(frozen=True)
class GitHubProviderError(Exception):
    code: str
    status: int = 502


_PROJECTS_QUERY = """query Projects($login: String!, $after: String) {
  user(login: $login) { projectsV2(first: 50, after: $after) { nodes { id number title url } pageInfo { hasNextPage endCursor } } }
  organization(login: $login) { projectsV2(first: 50, after: $after) { nodes { id number title url } pageInfo { hasNextPage endCursor } } }
}"""
_ITEMS_QUERY = """query ProjectItems($owner: String!, $number: Int!, $after: String) {
  user(login: $owner) { projectV2(number: $number) { items(first: 50, after: $after) { nodes { id content { ... on Issue { id number title url state repository { nameWithOwner } } } } pageInfo { hasNextPage endCursor } } } }
  organization(login: $owner) { projectV2(number: $number) { items(first: 50, after: $after) { nodes { id content { ... on Issue { id number title url state repository { nameWithOwner } } } } pageInfo { hasNextPage endCursor } } } }
}"""
_DISCOVERY_QUERY = """query ViewerAndOrganizations {
  viewer { login organizations(first: 100) { nodes { login } } }
}"""
_REPOSITORIES_QUERY = """query Repositories($owner: String!, $after: String) {
  repositoryOwner(login: $owner) {
    repositories(first: 50, after: $after, orderBy: {field: NAME, direction: ASC}) {
      nodes { name nameWithOwner url isArchived }
      pageInfo { hasNextPage endCursor }
    }
  }
}"""
_ISSUE_QUERY = """query Issue($owner: String!, $repo: String!, $number: Int!) {
  repository(owner: $owner, name: $repo) { issue(number: $number) { id number title body url state labels(first: 20) { nodes { name color } } } }
}"""
_VIEWER_LOGIN_QUERY = "query ViewerLogin { viewer { login } }"
_ISSUES_QUERY = """query RepositoryIssues($owner: String!, $repo: String!, $states: [IssueState!], $after: String) {
  repository(owner: $owner, name: $repo) {
    issues(first: 50, after: $after, states: $states) {
      nodes { id number title body url state updatedAt labels(first: 50) { nodes { name } } assignees(first: 50) { nodes { login } } }
      pageInfo { hasNextPage endCursor }
    }
  }
}"""
_UPDATE_ISSUE_MUTATION = """mutation UpdateIssue($input: UpdateIssueInput!) {
  updateIssue(input: $input) { issue { id number title body url state updatedAt labels(first: 50) { nodes { name } } assignees(first: 50) { nodes { login } } } }
}"""
_ASSIGNED_ISSUES_QUERY = """query AssignedIssues($owner: String!, $repo: String!, $assignee: String!, $after: String) {
  repository(owner: $owner, name: $repo) {
    issues(first: 50, after: $after, states: OPEN, filterBy: {assignee: $assignee}) {
      nodes { id number title url state repository { nameWithOwner } }
      pageInfo { hasNextPage endCursor }
    }
  }
}"""


def _project_token(project_id: str | None, repository: str | None = None) -> str | None:
    if not project_id:
        return None
    project = project_config.get(project_id)
    if not project:
        return None
    if repository:
        configured = (project.get("git_repos") or {}).get(repository) or {}
        if configured.get("git_token"):
            return configured["git_token"]
    if project.get("git_token"):
        return project["git_token"]
    for configured in (project.get("git_repos") or {}).values():
        if isinstance(configured, dict) and configured.get("git_token"):
            return configured["git_token"]
    return None


def _credential(username: str, name: str, project_id: str | None = None, repository: str | None = None):
    if name == PROJECT_TOKEN_REF:
        token = _project_token(project_id, repository)
        if not token:
            raise GitHubProviderError("github_project_token_unavailable", 424)
        return token
    credential = get_credential(username, name)
    if credential is None or credential.type != "bearer" or not credential.value:
        raise GitHubProviderError("github_credential_unavailable", 424)
    return credential.value


def _post(username: str, credential_name: str, query: str, variables: dict[str, Any], *, project_id: str | None = None, repository: str | None = None) -> dict:
    token = _credential(username, credential_name, project_id, repository)
    try:
        response = httpx.post(
            GITHUB_GRAPHQL_URL,
            json={"query": query, "variables": variables},
            headers={"Accept": "application/json", "Authorization": f"Bearer {token}"},
            timeout=_TIMEOUT,
        )
    except httpx.TimeoutException as exc:
        raise GitHubProviderError("github_timeout", 504) from exc
    except httpx.HTTPError as exc:
        raise GitHubProviderError("github_unavailable", 502) from exc
    if response.status_code == 401:
        raise GitHubProviderError("github_unauthorized", 502)
    if response.status_code == 403:
        raise GitHubProviderError("github_forbidden", 502)
    if response.status_code == 429:
        raise GitHubProviderError("github_rate_limited", 429)
    if response.status_code >= 400:
        raise GitHubProviderError("github_http_error", 502)
    try:
        payload = response.json()
    except ValueError as exc:
        raise GitHubProviderError("github_invalid_response", 502) from exc
    errors = payload.get("errors") or []
    if errors:
        message = str(errors[0].get("type", "")).upper()
        code = "github_forbidden" if "FORBIDDEN" in message else "github_query_failed"
        raise GitHubProviderError(code, 502)
    data = payload.get("data")
    if not isinstance(data, dict):
        raise GitHubProviderError("github_invalid_response", 502)
    return data


def discover_owners(username: str, credential_name: str, project_id: str | None = None) -> list[dict]:
    data = _post(username, credential_name, _DISCOVERY_QUERY, {}, project_id=project_id)
    viewer = data.get("viewer") or {}
    login = viewer.get("login")
    organizations = (viewer.get("organizations") or {}).get("nodes") or []
    owners = ([{"login": login, "kind": "user"}] if login else [])
    owners.extend({"login": item.get("login"), "kind": "organization"} for item in organizations if item.get("login"))
    return owners


def list_repositories(username: str, credential_name: str, owner: str, project_id: str | None = None) -> list[dict]:
    result: list[dict] = []
    after = None
    for _ in range(_MAX_PAGES):
        data = _post(username, credential_name, _REPOSITORIES_QUERY, {"owner": owner, "after": after}, project_id=project_id)
        container = (data.get("repositoryOwner") or {}).get("repositories") or {}
        result.extend(item for item in (container.get("nodes") or []) if not item.get("isArchived"))
        page = container.get("pageInfo") or {}
        if not page.get("hasNextPage"):
            return result
        after = page.get("endCursor")
        if not after:
            break
    raise GitHubProviderError("github_pagination_limit", 502)


def connection_check(username: str, credential_name: str, project_id: str | None = None) -> dict:
    data = _post(username, credential_name, "query Viewer { viewer { login } }", {}, project_id=project_id)
    viewer = data.get("viewer") or {}
    return {"ok": bool(viewer.get("login")), "login": viewer.get("login")}


def list_projects(username: str, credential_name: str, owner: str, project_id: str | None = None) -> list[dict]:
    result: list[dict] = []
    after = None
    for _ in range(_MAX_PAGES):
        data = _post(username, credential_name, _PROJECTS_QUERY, {"login": owner, "after": after}, project_id=project_id)
        container = (data.get("user") or data.get("organization") or {}).get("projectsV2") or {}
        result.extend(container.get("nodes") or [])
        page = container.get("pageInfo") or {}
        if not page.get("hasNextPage"):
            return result
        after = page.get("endCursor")
        if not after:
            break
    raise GitHubProviderError("github_pagination_limit", 502)


def list_project_items(username: str, credential_name: str, owner: str, number: int, project_id: str | None = None) -> list[dict]:
    result: list[dict] = []
    after = None
    for _ in range(_MAX_PAGES):
        data = _post(username, credential_name, _ITEMS_QUERY, {"owner": owner, "number": number, "after": after}, project_id=project_id)
        container = (data.get("user") or data.get("organization") or {}).get("projectV2") or {}
        items = container.get("items") or {}
        result.extend(items.get("nodes") or [])
        page = items.get("pageInfo") or {}
        if not page.get("hasNextPage"):
            return result
        after = page.get("endCursor")
        if not after:
            break
    raise GitHubProviderError("github_pagination_limit", 502)


def list_issues(
    username: str,
    credential_name: str,
    owner: str,
    repository: str,
    state: str = "open",
    project_id: str | None = None,
) -> list[dict]:
    states = {"open": ["OPEN"], "closed": ["CLOSED"], "all": None}.get(state)
    if state not in {"open", "closed", "all"}:
        raise GitHubProviderError("github_invalid_issue_state", 400)
    result: list[dict] = []
    after = None
    for _ in range(_MAX_PAGES):
        data = _post(
            username,
            credential_name,
            _ISSUES_QUERY,
            {"owner": owner, "repo": repository, "states": states, "after": after},
            project_id=project_id,
            repository=repository,
        )
        issues = ((data.get("repository") or {}).get("issues") or {})
        result.extend(issues.get("nodes") or [])
        page = issues.get("pageInfo") or {}
        if not page.get("hasNextPage"):
            return result
        after = page.get("endCursor")
        if not after:
            break
    raise GitHubProviderError("github_pagination_limit", 502)


def list_assigned_issues(username: str, credential_name: str, owner: str, repository: str, project_id: str | None = None) -> list[dict]:
    viewer_data = _post(
        username, credential_name, _VIEWER_LOGIN_QUERY, {}, project_id=project_id, repository=repository
    )
    login = (viewer_data.get("viewer") or {}).get("login")
    if not login:
        raise GitHubProviderError("github_viewer_not_found", 502)
    result: list[dict] = []
    after = None
    for _ in range(_MAX_PAGES):
        data = _post(
            username,
            credential_name,
            _ASSIGNED_ISSUES_QUERY,
            {"owner": owner, "repo": repository, "assignee": login, "after": after},
            project_id=project_id,
            repository=repository,
        )
        issues = ((data.get("repository") or {}).get("issues") or {})
        result.extend(issues.get("nodes") or [])
        page = issues.get("pageInfo") or {}
        if not page.get("hasNextPage"):
            return result
        after = page.get("endCursor")
        if not after:
            break
    raise GitHubProviderError("github_pagination_limit", 502)


def get_issue(username: str, credential_name: str, owner: str, repository: str, number: int, project_id: str | None = None) -> dict:
    data = _post(username, credential_name, _ISSUE_QUERY, {"owner": owner, "repo": repository, "number": number}, project_id=project_id, repository=repository)
    issue = (data.get("repository") or {}).get("issue")
    if not issue:
        raise GitHubProviderError("github_issue_not_found", 404)
    return issue


def update_issue(
    username: str,
    credential_name: str,
    owner: str,
    repository: str,
    node_id: str,
    *,
    title: str | None = None,
    body: str | None = None,
    state: str | None = None,
    project_id: str | None = None,
) -> dict:
    input_data: dict[str, Any] = {"issueId": node_id}
    if title is not None:
        input_data["title"] = title
    if body is not None:
        input_data["body"] = body
    if state is not None:
        input_data["state"] = state.upper()
    if len(input_data) == 1:
        raise GitHubProviderError("github_issue_update_empty", 400)
    data = _post(
        username,
        credential_name,
        _UPDATE_ISSUE_MUTATION,
        {"input": input_data},
        project_id=project_id,
        repository=repository,
    )
    issue = (data.get("updateIssue") or {}).get("issue")
    if not issue:
        raise GitHubProviderError("github_issue_update_failed", 502)
    return issue
