"""Hydra-Labor L2: GitHub-Zugriff – nur feste Adressen, Token nur im Kopf, Fehler als Code."""
from __future__ import annotations

import asyncio

import httpx
import pytest
from backend import github_api

TOKEN = "gho_SECRETsecret0123456789"


@pytest.fixture
def seen(monkeypatch):
    got: list[httpx.Request] = []

    def handler(req: httpx.Request) -> httpx.Response:
        got.append(req)
        if req.url.host == "api.github.com":
            return httpx.Response(200, json={"login": "x"}, headers={"X-OAuth-Scopes": "public_repo"})
        return httpx.Response(200, json={"device_code": "d"})
    real = httpx.AsyncClient

    def client(**kw):
        assert kw.get("follow_redirects") is False
        return real(transport=httpx.MockTransport(handler), **kw)
    monkeypatch.setattr(github_api.httpx, "AsyncClient", client)
    return got


def run(c):
    return asyncio.run(c)


def test_api_mit_token_nur_im_kopf(seen):
    st, body, hdr = run(github_api.request("GET", "https://api.github.com/user", token=TOKEN))
    assert (st, body["login"], hdr["x-oauth-scopes"]) == (200, "x", "public_repo")
    req = seen[0]
    assert req.headers["authorization"] == f"Bearer {TOKEN}"
    assert TOKEN not in str(req.url)
    assert req.headers["accept"] == "application/vnd.github+json"
    assert req.headers["x-github-api-version"] == "2022-11-28"


def test_login_ohne_token_formular(seen):
    run(github_api.request("POST", "https://github.com/login/device/code", data={"client_id": "c", "scope": "s"}))
    req = seen[0]
    assert "authorization" not in req.headers and req.headers["accept"] == "application/json"
    assert req.content == b"client_id=c&scope=s"


@pytest.mark.parametrize("url", ["https://evil.example/user", "http://api.github.com/user",
                                 "https://api.github.com.evil.example/x", "https://github.com/hydrahive",
                                 "https://github.com/login/oauth/authorize", "file:///etc/passwd"])
def test_fremde_adressen_abgelehnt(seen, url):
    with pytest.raises(github_api.GitHubError) as e:
        run(github_api.request("GET", url, token=TOKEN))
    assert e.value.code == "labor_github_url" and seen == []


def test_nicht_erreichbar(monkeypatch):
    def handler(req):
        raise httpx.ConnectError("weg")
    real = httpx.AsyncClient
    monkeypatch.setattr(github_api.httpx, "AsyncClient", lambda **kw: real(transport=httpx.MockTransport(handler), **kw))
    with pytest.raises(github_api.GitHubError) as e:
        run(github_api.request("GET", "https://api.github.com/user"))
    assert e.value.code == "labor_github_unreachable"


def test_liste_und_leere_antwort(monkeypatch):
    answers = [httpx.Response(200, json=[{"a": 1}]), httpx.Response(204), httpx.Response(502, text="kaputt"),
               httpx.Response(200, content=b"")]
    real = httpx.AsyncClient
    monkeypatch.setattr(github_api.httpx, "AsyncClient",
                        lambda **kw: real(transport=httpx.MockTransport(lambda r: answers.pop(0)), **kw))
    assert run(github_api.request("GET", "https://api.github.com/x"))[1] == {"items": [{"a": 1}]}
    assert run(github_api.request("GET", "https://api.github.com/x"))[:2] == (204, {})
    assert run(github_api.request("GET", "https://api.github.com/x"))[:2] == (502, {})
    assert run(github_api.request("GET", "https://api.github.com/x"))[:2] == (200, {})
