"""Hydra-Labor L3: Anmeldung an der Durchreiche (Muster Kern-AgentLink-Dashboard) – Ticket → Cookie → Prüfung für nginx."""
from __future__ import annotations

import time

import pytest
from backend import probe_auth, state

B = "/api/modules/hydralabor"
# Ohne HydraHive-Login (Browser auf :8443 bzw. nginx auth_request) → Geräte-Weg des Kerns mit Bremse.
LOGIN = "/api/module-device/hydralabor/probe/login"
AUTH = "/api/module-device/hydralabor/probe/auth"


@pytest.fixture
def ready(db_ready):
    state.clear()
    state.set_step("ready")
    probe_auth._tickets.clear()
    yield
    state.clear()
    probe_auth._tickets.clear()


def ticket_from(client, headers, host="labor.example"):
    r = client.post(B + "/probe/open", headers={**headers, "Host": host}, json={})
    assert r.status_code == 200, r.text
    url = r.json()["url"]
    assert url.startswith(f"https://{host}:8443/__labor_login?t=")
    return url.split("t=", 1)[1]


def test_ticket_ohne_login(client, ready):
    assert client.post(B + "/probe/open", json={}).status_code == 401


def test_ticket_nur_fuer_admins(client, user_headers, ready):
    assert client.post(B + "/probe/open", headers=user_headers, json={}).status_code == 403


def test_ticket_nur_wenn_labor_fertig(client, admin_headers, db_ready):
    state.clear()
    assert client.post(B + "/probe/open", headers=admin_headers, json={}).status_code == 409


def test_ticket_einloesen_setzt_cookie(client, admin_headers, ready):
    t = ticket_from(client, admin_headers)
    r = client.get(LOGIN, params={"t": t}, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/"
    sc = r.headers["set-cookie"]
    assert sc.startswith("hh_labor_probe=")
    parts = [x.strip().lower() for x in sc.split(";")]
    for part in ("HttpOnly", "Secure", "SameSite=strict", "Path=/", "Max-Age=28800"):
        assert part.lower() in parts


def test_ticket_nur_einmal(client, admin_headers, ready):
    t = ticket_from(client, admin_headers)
    assert client.get(LOGIN, params={"t": t}, follow_redirects=False).status_code == 303
    assert client.get(LOGIN, params={"t": t}, follow_redirects=False).status_code == 401


def test_ticket_abgelaufen(client, admin_headers, ready, monkeypatch):
    t = ticket_from(client, admin_headers)
    real = time.time
    monkeypatch.setattr(probe_auth.time, "time", lambda: real() + 61)
    assert client.get(LOGIN, params={"t": t}, follow_redirects=False).status_code == 401


@pytest.mark.parametrize("t", ["", "x" * 600, "falsch"])
def test_ticket_falsch(client, ready, t):
    assert client.get(LOGIN, params={"t": t}, follow_redirects=False).status_code in (401, 422)


def test_pruefung_mit_cookie(client, admin_headers, ready):
    t = ticket_from(client, admin_headers)
    cookie = client.get(LOGIN, params={"t": t}, follow_redirects=False).cookies.get("hh_labor_probe")
    client.cookies.clear()
    assert client.get(AUTH, headers={"Cookie": f"hh_labor_probe={cookie}"}).status_code == 204


@pytest.mark.parametrize("cookie", ["", "x", "a.b", "a.b.c", "x" * 600])
def test_pruefung_ohne_gueltiges_cookie(client, ready, cookie):
    client.cookies.clear()
    hdr = {"Cookie": f"hh_labor_probe={cookie}"} if cookie else {}
    assert client.get(AUTH, headers=hdr).status_code == 401


def test_cookie_gefaelscht(client, admin_headers, ready):
    t = ticket_from(client, admin_headers)
    cookie = client.get(LOGIN, params={"t": t}, follow_redirects=False).cookies.get("hh_labor_probe")
    body, sig = cookie.split(".")
    client.cookies.clear()
    assert client.get(AUTH, headers={"Cookie": f"hh_labor_probe={body}.{sig[:-2]}AA"}).status_code == 401


def test_cookie_abgelaufen(client, admin_headers, ready, monkeypatch):
    t = ticket_from(client, admin_headers)
    cookie = client.get(LOGIN, params={"t": t}, follow_redirects=False).cookies.get("hh_labor_probe")
    real = time.time
    monkeypatch.setattr(probe_auth.time, "time", lambda: real() + 8 * 3600 + 5)
    client.cookies.clear()
    assert client.get(AUTH, headers={"Cookie": f"hh_labor_probe={cookie}"}).status_code == 401


def test_cookie_nutzer_kein_admin_mehr(client, admin_headers, ready, monkeypatch):
    t = ticket_from(client, admin_headers)
    cookie = client.get(LOGIN, params={"t": t}, follow_redirects=False).cookies.get("hh_labor_probe")
    from hydrahive.api.middleware import users
    real = users.get_by_id
    monkeypatch.setattr(users, "get_by_id", lambda uid: {**(real(uid) or {}), "role": "user"})
    client.cookies.clear()
    assert client.get(AUTH, headers={"Cookie": f"hh_labor_probe={cookie}"}).status_code == 401


def test_cookie_ist_kein_login_token(client, admin_headers, ready):
    """Das Probe-Cookie öffnet keine API des echten HydraHive."""
    t = ticket_from(client, admin_headers)
    cookie = client.get(LOGIN, params={"t": t}, follow_redirects=False).cookies.get("hh_labor_probe")
    client.cookies.clear()
    assert client.get(B + "/state", headers={"Authorization": f"Bearer {cookie}"}).status_code == 401
    assert client.get(B + "/state", headers={"Cookie": f"hh_labor_probe={cookie}"}).status_code == 401


def test_schluessel_zweckgebunden():
    from hydrahive.settings import settings
    assert probe_auth._key() != settings.secret_key.encode()
    import hashlib
    import hmac
    assert probe_auth._key() != hmac.new(settings.secret_key.encode(), b"hydrahive-agentlink-dashboard-v1",
                                         hashlib.sha256).digest()


@pytest.mark.parametrize("host", ["labor.example", "192.168.178.2", "[fd00::1]", "server.tail1234.ts.net"])
def test_adresse_aus_host(client, admin_headers, ready, host):
    ticket_from(client, admin_headers, host=host)


@pytest.mark.parametrize("host", ["evil.example/x", "a b", "x\"y", "foo@bar"])
def test_komischer_host_abgelehnt(client, admin_headers, ready, host):
    r = client.post(B + "/probe/open", headers={**admin_headers, "Host": host}, json={})
    assert r.status_code == 400


def test_nicht_unter_login_pfad(client, ready):
    """Unter /api/modules/… gäbe es die Prüfung nur mit HydraHive-Login – dort darf sie nicht hängen."""
    client.cookies.clear()
    assert client.get("/api/modules/hydralabor/probe/auth").status_code in (401, 404)
    assert client.get("/api/modules/hydralabor/probe/login", params={"t": "x"}).status_code in (401, 404)


def test_tickets_begrenzt(client, admin_headers, ready):
    for _ in range(probe_auth.MAX_TICKETS + 5):
        ticket_from(client, admin_headers)
    assert len(probe_auth._tickets) <= probe_auth.MAX_TICKETS


def test_host_mit_port_wird_8443(client, admin_headers, ready):
    r = client.post(B + "/probe/open", headers={**admin_headers, "Host": "labor.example:8001"}, json={})
    assert r.json()["url"].startswith("https://labor.example:8443/__labor_login?t=")


def test_ticket_nutzer_kein_admin_mehr(client, admin_headers, ready, monkeypatch):
    t = ticket_from(client, admin_headers)
    from hydrahive.api.middleware import users
    real = users.get_by_id
    monkeypatch.setattr(users, "get_by_id", lambda uid: {**(real(uid) or {}), "role": "user"})
    assert client.get(LOGIN, params={"t": t}, follow_redirects=False).status_code == 401


def test_zu_langes_cookie_trotz_signatur(ready, monkeypatch):
    monkeypatch.setattr(probe_auth, "_is_admin", lambda uid: True)
    assert probe_auth.admin_from(probe_auth.issue_cookie("u"))
    long = probe_auth.issue_cookie("u" * 600)
    assert len(long) > probe_auth._MAX_LEN and not probe_auth.admin_from(long)
