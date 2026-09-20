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
