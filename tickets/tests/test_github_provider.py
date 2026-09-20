from __future__ import annotations

import httpx
import pytest

from backend import github_provider as provider


class Response:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


def test_connection_check_uses_bearer_credential_without_logging(monkeypatch):
    calls = []

    class Credential:
        type = "bearer"
        value = "super-secret-token"

    monkeypatch.setattr(provider, "get_credential", lambda username, name: Credential())
    monkeypatch.setattr(
        httpx, "post", lambda *args, **kwargs: (calls.append((args, kwargs)) or Response(200, {"data": {"viewer": {"login": "flowki"}}}))
    )

    assert provider.connection_check("admin", "github") == {"ok": True, "login": "flowki"}
    assert calls[0][0][0] == provider.GITHUB_GRAPHQL_URL
    assert calls[0][1]["headers"]["Authorization"] == "Bearer super-secret-token"
    assert "super-secret-token" not in str(provider.connection_check.__dict__)


def test_provider_rejects_non_bearer_or_missing_credentials(monkeypatch):
    class Credential:
        type = "basic"
        value = "secret"

    monkeypatch.setattr(provider, "get_credential", lambda username, name: Credential())
    with pytest.raises(provider.GitHubProviderError, match="github_credential_unavailable"):
        provider.connection_check("admin", "github")


def test_projects_pagination_is_bounded_and_uses_cursor(monkeypatch):
    class Credential:
        type = "bearer"
        value = "token"

    calls = []
    monkeypatch.setattr(provider, "get_credential", lambda username, name: Credential())

    def post(url, **kwargs):
        calls.append(kwargs["json"]["variables"])
        after = kwargs["json"]["variables"]["after"]
        if after is None:
            return Response(200, {"data": {"user": {"projectsV2": {
                "nodes": [{"number": 1}], "pageInfo": {"hasNextPage": True, "endCursor": "cursor-1"}
            }}}})
        return Response(200, {"data": {"user": {"projectsV2": {
            "nodes": [{"number": 2}], "pageInfo": {"hasNextPage": False, "endCursor": None}
        }}}})

    monkeypatch.setattr(httpx, "post", post)
    assert provider.list_projects("admin", "github", "owner") == [{"number": 1}, {"number": 2}]
    assert [call["after"] for call in calls] == [None, "cursor-1"]


def test_timeout_and_graphql_errors_are_stable(monkeypatch):
    class Credential:
        type = "bearer"
        value = "token"

    monkeypatch.setattr(provider, "get_credential", lambda username, name: Credential())
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: (_ for _ in ()).throw(httpx.TimeoutException("slow")))
    with pytest.raises(provider.GitHubProviderError, match="github_timeout"):
        provider.connection_check("admin", "github")

    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: Response(200, {"errors": [{"type": "FORBIDDEN"}]}))
    with pytest.raises(provider.GitHubProviderError, match="github_forbidden"):
        provider.connection_check("admin", "github")


def test_discovery_returns_user_and_organizations(monkeypatch):
    class Credential:
        type = "bearer"
        value = "token"

    monkeypatch.setattr(provider, "get_credential", lambda username, name: Credential())
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: Response(200, {"data": {
        "viewer": {"login": "flowki", "organizations": {"nodes": [{"login": "hydrahive"}]}}
    }}))
    assert provider.discover_owners("admin", "github") == [
        {"login": "flowki", "kind": "user"},
        {"login": "hydrahive", "kind": "organization"},
    ]


def test_repository_discovery_filters_archived_repositories(monkeypatch):
    class Credential:
        type = "bearer"
        value = "token"

    monkeypatch.setattr(provider, "get_credential", lambda username, name: Credential())
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: Response(200, {"data": {
        "repositoryOwner": {"repositories": {"nodes": [
            {"name": "active", "isArchived": False}, {"name": "old", "isArchived": True}
        ], "pageInfo": {"hasNextPage": False, "endCursor": None}}}
    }}))
    assert provider.list_repositories("admin", "github", "flowki") == [{"name": "active", "isArchived": False}]


def test_assigned_issues_use_viewer_and_open_state(monkeypatch):
    class Credential:
        type = "bearer"
        value = "token"

    monkeypatch.setattr(provider, "get_credential", lambda username, name: Credential())
    calls = []

    def post(url, **kwargs):
        query = kwargs["json"]["query"]
        calls.append(kwargs["json"])
        if "ViewerLogin" in query:
            return Response(200, {"data": {"viewer": {"login": "flowki"}}})
        return Response(200, {"data": {"repository": {"issues": {
            "nodes": [{"number": 7, "title": "Fix me"}],
            "pageInfo": {"hasNextPage": False, "endCursor": None},
        }}}})

    monkeypatch.setattr(httpx, "post", post)
    assert provider.list_assigned_issues("admin", "github", "gh0stOo", "flowki-studio") == [{"number": 7, "title": "Fix me"}]
    assert calls[1]["variables"] == {"owner": "gh0stOo", "repo": "flowki-studio", "assignee": "flowki", "after": None}
    assert "states: OPEN" in calls[1]["query"]


def test_list_issues_returns_remote_snapshot(monkeypatch):
    class Credential:
        type = "bearer"
        value = "token"

    monkeypatch.setattr(provider, "get_credential", lambda username, name: Credential())
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: Response(200, {"data": {
        "repository": {"issues": {
            "nodes": [{
                "id": "I_1", "number": 12, "title": "Fix sync", "body": "Details",
                "url": "https://github.com/o/r/issues/12", "state": "OPEN", "updatedAt": "2026-01-01T00:00:00Z",
                "labels": {"nodes": [{"name": "bug"}]}, "assignees": {"nodes": [{"login": "flowki"}]},
            }], "pageInfo": {"hasNextPage": False, "endCursor": None}
        }}
    }}))
    assert provider.list_issues("admin", "github", "o", "r") == [{
        "id": "I_1", "number": 12, "title": "Fix sync", "body": "Details",
        "url": "https://github.com/o/r/issues/12", "state": "OPEN", "updatedAt": "2026-01-01T00:00:00Z",
        "labels": {"nodes": [{"name": "bug"}]}, "assignees": {"nodes": [{"login": "flowki"}]},
    }]


def test_update_issue_uses_mutation_input_without_secret(monkeypatch):
    class Credential:
        type = "bearer"
        value = "token"

    monkeypatch.setattr(provider, "get_credential", lambda username, name: Credential())
    calls = []

    def post(url, **kwargs):
        calls.append(kwargs["json"])
        return Response(200, {"data": {"updateIssue": {"issue": {"id": "I_1", "title": "Updated", "state": "OPEN"}}}})

    monkeypatch.setattr(httpx, "post", post)
    result = provider.update_issue("admin", "github", "o", "r", "I_1", title="Updated", state="open")
    assert result["title"] == "Updated"
    assert calls[0]["variables"] == {"input": {"issueId": "I_1", "title": "Updated", "state": "OPEN"}}
    assert "token" not in str(calls[0])


def test_project_token_reference_uses_project_config_without_vault(monkeypatch):
    class ResponseWithHeader(Response):
        pass

    monkeypatch.setattr(provider.project_config, "get", lambda project_id: {
        "git_token": "project-token", "git_repos": {}
    })
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: ResponseWithHeader(200, {"data": {"viewer": {"login": "flowki"}}}))
    assert provider.connection_check("unused-user", provider.PROJECT_TOKEN_REF, "project-1") == {
        "ok": True, "login": "flowki"
    }
