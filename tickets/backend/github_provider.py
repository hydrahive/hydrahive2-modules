"""Small, read-only GitHub GraphQL provider with strict network boundaries."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from hydrahive.credentials.store import get_credential

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
_ISSUE_QUERY = """query Issue($owner: String!, $repo: String!, $number: Int!) {
  repository(owner: $owner, name: $repo) { issue(number: $number) { id number title body url state labels(first: 20) { nodes { name color } } } }
}"""


def _credential(username: str, name: str):
    credential = get_credential(username, name)
    if credential is None or credential.type != "bearer" or not credential.value:
        raise GitHubProviderError("github_credential_unavailable", 424)
    return credential


def _post(username: str, credential_name: str, query: str, variables: dict[str, Any]) -> dict:
    credential = _credential(username, credential_name)
    try:
        response = httpx.post(
            GITHUB_GRAPHQL_URL,
            json={"query": query, "variables": variables},
            headers={"Accept": "application/json", "Authorization": f"Bearer {credential.value}"},
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


def connection_check(username: str, credential_name: str) -> dict:
    data = _post(username, credential_name, "query Viewer { viewer { login } }", {})
    viewer = data.get("viewer") or {}
    return {"ok": bool(viewer.get("login")), "login": viewer.get("login")}


def list_projects(username: str, credential_name: str, owner: str) -> list[dict]:
    result: list[dict] = []
    after = None
    for _ in range(_MAX_PAGES):
        data = _post(username, credential_name, _PROJECTS_QUERY, {"login": owner, "after": after})
        container = (data.get("user") or data.get("organization") or {}).get("projectsV2") or {}
        result.extend(container.get("nodes") or [])
        page = container.get("pageInfo") or {}
        if not page.get("hasNextPage"):
            return result
        after = page.get("endCursor")
        if not after:
            break
    raise GitHubProviderError("github_pagination_limit", 502)


def list_project_items(username: str, credential_name: str, owner: str, number: int) -> list[dict]:
    result: list[dict] = []
    after = None
    for _ in range(_MAX_PAGES):
        data = _post(username, credential_name, _ITEMS_QUERY, {"owner": owner, "number": number, "after": after})
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


def get_issue(username: str, credential_name: str, owner: str, repository: str, number: int) -> dict:
    data = _post(username, credential_name, _ISSUE_QUERY, {"owner": owner, "repo": repository, "number": number})
    issue = (data.get("repository") or {}).get("issue")
    if not issue:
        raise GitHubProviderError("github_issue_not_found", 404)
    return issue
