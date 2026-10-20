"""Routen (/api/modules/legal/…) und Agent-Werkzeuge legal_search / legal_norm (Plan L1 Schritte 6–7).

Das Kern-Tor (Freigabe ``module.legal`` + Vault-PIN, ``api/main.py`` mount_module_routers) ist Kern-Sache und
wird live auf hydratest geprüft; hier hängen die Router wie in den anderen Modul-Suites direkt an der App.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from backend import corpus_store, corpus_sync, gii_fetch
from backend.gii_parse import parse_law
from conftest import fixture_xml
from fastapi.testclient import TestClient

PREFIX = "/api/modules/legal"


@pytest.fixture(scope="module")
def app_client(setup_test_env):
    from contextlib import asynccontextmanager

    from backend.routes import router
    from fastapi import FastAPI
    from hydrahive.api import main
    if not any(getattr(r, "path", "").startswith(PREFIX) for r in main.app.routes):
        main.app.include_router(router, prefix=PREFIX)

    @asynccontextmanager
    async def minimal_lifespan(app: FastAPI):
        from hydrahive.settings import settings
        settings.ensure_dirs()
        yield

    orig = main.app.router.lifespan_context
    main.app.router.lifespan_context = minimal_lifespan
    with TestClient(main.app) as c:
        yield c
    main.app.router.lifespan_context = orig


def _login(client, user):
    r = client.post("/api/auth/login", json={"username": user, "password": "testpass123"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def corpus():
    for key in ("bgb", "vwgo", "owig_1968"):
        xml = fixture_xml(key)
        corpus_store.save_law(parse_law(key, xml), xml, fetched_at="2026-10-20T03:30:00Z", pinned=True)


# ── Routen ────────────────────────────────────────────────────────────────────

def test_laws_list_and_detail(app_client, corpus):
    h = _login(app_client, "alice")
    laws = app_client.get(f"{PREFIX}/laws", headers=h).json()
    bgb = next(law for law in laws["laws"] if law["key"] == "bgb")
    assert bgb["abbr"] == "BGB" and bgb["norms"] == 7 and bgb["group"] == "Zivil- und Verfahrensrecht"
    assert laws["core_total"] == 54
    detail = app_client.get(f"{PREFIX}/laws/bgb", headers=h).json()
    assert [n["enbez"] for n in detail["norms"]][:3] == ["§ 535", "§ 536", "§ 536c"]
    assert app_client.get(f"{PREFIX}/laws/gibtsnicht", headers=h).status_code == 404


def test_norm_route_with_link_and_stand(app_client, corpus):
    h = _login(app_client, "alice")
    r = app_client.get(f"{PREFIX}/norm", params={"citation": "§ 536c BGB"}, headers=h)
    n = r.json()
    assert r.status_code == 200
    assert n["enbez"] == "§ 536c" and n["text"].startswith("(1) Zeigt sich")
    assert n["url"] == "https://www.gesetze-im-internet.de/bgb/__536c.html"
    assert "Neugefasst" in n["stand"]
    assert app_client.get(f"{PREFIX}/norm", params={"citation": "§ 9999 BGB"}, headers=h).status_code == 404
    assert app_client.get(f"{PREFIX}/norm", params={"citation": "Quatsch"}, headers=h).status_code == 422


def test_search_route(app_client, corpus):
    h = _login(app_client, "alice")
    r = app_client.get(f"{PREFIX}/search", params={"q": "Mangel Mietsache Anzeige Mieter", "limit": 3}, headers=h)
    assert r.status_code == 200
    assert ("BGB", "§ 536c") in [(x["abbr"], x["enbez"]) for x in r.json()["hits"]]
    assert app_client.get(f"{PREFIX}/search", params={"q": "  "}, headers=h).status_code == 422
    assert app_client.get(f"{PREFIX}/search", params={"q": "x" * 501}, headers=h).status_code == 422


def test_sync_is_admin_only_and_status_readable(app_client, corpus, monkeypatch):
    async def fetch(key):
        return fixture_xml(key)
    monkeypatch.setattr(gii_fetch, "fetch_law_xml", fetch)
    monkeypatch.setattr(corpus_sync, "PAUSE_SECONDS", 0)
    monkeypatch.setattr(corpus_sync, "keys_to_sync", lambda: ["bgb"])
    user, admin = _login(app_client, "alice"), _login(app_client, "root")
    assert app_client.post(f"{PREFIX}/sync", headers=user).status_code == 403
    assert app_client.post(f"{PREFIX}/sync", headers=admin).status_code == 202
    for _ in range(50):
        st = app_client.get(f"{PREFIX}/sync", headers=user).json()
        if st["last"] and st["last"]["state"] != "running":
            break
        asyncio.run(asyncio.sleep(0.05))
    assert st["last"]["state"] == "done" and st["last"]["total"] == 1


def test_routes_require_login(app_client):
    assert app_client.get(f"{PREFIX}/laws").status_code == 401


# ── Werkzeuge ─────────────────────────────────────────────────────────────────

def _ctx():
    from hydrahive.tools.base import ToolContext
    return ToolContext(session_id="s", agent_id="a", user_id="alice", workspace=Path("/tmp"))


def _run(tool, args):
    return asyncio.run(tool.execute(args, _ctx()))


def test_tool_search_finds_and_explains(corpus):
    from backend.tools import LEGAL_SEARCH
    res = _run(LEGAL_SEARCH, {"query": "Mangel Mietsache Anzeige Mieter", "limit": 3})
    assert res.success
    assert ("BGB", "§ 536c") in [(h["abbr"], h["enbez"]) for h in res.output["hits"]]
    assert "Fachbegriff" in LEGAL_SEARCH.description
    assert LEGAL_SEARCH.schema["properties"]["limit"]["maximum"] == 20


def test_tool_search_hint_when_nothing_found(corpus):
    from backend.tools import LEGAL_SEARCH
    res = _run(LEGAL_SEARCH, {"query": "Raumfahrt Mondlandung"})
    assert res.success and res.output["hits"] == []
    assert "anderen Fachbegriffen" in res.output["hint"]


def test_tool_norm_returns_wording_with_source(corpus):
    from backend.tools import LEGAL_NORM
    res = _run(LEGAL_NORM, {"citation": "§ 70 VwGO"})
    assert res.success
    out = res.output
    assert out["citation"] == "§ 70 VwGO"
    assert out["text"].startswith("(1) Der Widerspruch ist innerhalb eines Monats")
    assert out["url"] == "https://www.gesetze-im-internet.de/vwgo/__70.html"
    assert out["fetched_at"] == "2026-10-20T03:30:00Z"


def test_tool_norm_unknown_is_a_clear_failure(corpus):
    from backend.tools import LEGAL_NORM
    res = _run(LEGAL_NORM, {"citation": "§ 9999 BGB"})
    assert not res.success and "nicht im Korpus" in res.error
    res = _run(LEGAL_NORM, {"citation": "§ 1 XYZ"})
    assert not res.success and "XYZ" in res.error


def test_tool_norm_as_of_returns_old_version(corpus):
    from backend.tools import LEGAL_NORM
    changed = fixture_xml("bgb").replace("unverzüglich anzuzeigen".encode(), b"binnen einer Woche anzuzeigen")
    corpus_store.save_law(parse_law("bgb", changed), changed, fetched_at="2026-11-02T03:30:00Z", pinned=True)
    old = _run(LEGAL_NORM, {"citation": "§ 536c BGB", "as_of": "2026-10-25"})
    assert "unverzüglich" in old.output["text"] and old.output["valid_to"] == "2026-11-02T03:30:00Z"
    bad = _run(LEGAL_NORM, {"citation": "§ 536c BGB", "as_of": "gestern"})
    assert not bad.success


def test_empty_corpus_tells_agent_to_sync():
    from backend.tools import LEGAL_SEARCH
    res = _run(LEGAL_SEARCH, {"query": "Mietsicherheit"})
    assert not res.success and "noch keine Gesetze" in res.error


def test_as_of_with_timezone_is_converted_to_utc(corpus):
    """Neue Fassung ab 02.11. 03:30 UTC. 02.11. 04:00+02:00 = 02:00 UTC → noch die alte Fassung."""
    from backend.tools import LEGAL_NORM
    changed = fixture_xml("bgb").replace("unverzüglich anzuzeigen".encode(), b"binnen einer Woche anzuzeigen")
    corpus_store.save_law(parse_law("bgb", changed), changed, fetched_at="2026-11-02T03:30:00Z", pinned=True)
    before = _run(LEGAL_NORM, {"citation": "§ 536c BGB", "as_of": "2026-11-02T04:00:00+02:00"})
    after = _run(LEGAL_NORM, {"citation": "§ 536c BGB", "as_of": "2026-11-02T04:00:00Z"})
    assert "unverzüglich" in before.output["text"]
    assert "binnen einer Woche" in after.output["text"]
