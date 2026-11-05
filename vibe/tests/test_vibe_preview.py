"""Vibe Baustein 8: Vorschau – Ticket → Cookie → Prüfung für nginx, nginx-Block, Weg Server → Container."""
from __future__ import annotations

import time

import pytest
from backend import container, network, preview_auth, preview_net, preview_site, provision, state

from test_vibe_routes_gui import B, MODEL, _create, _ready, env  # noqa: F401  (Fixture `env` und Hilfen der Oberfläche)

LOGIN = "/api/module-device/vibe/preview/login"
AUTH = "/api/module-device/vibe/preview/auth"


@pytest.fixture
def proj(env, client, admin_headers):  # noqa: F811
    preview_auth._tickets.clear()
    preview_net._addr.clear()
    pid = _create(client, admin_headers).json()["project_id"]
    _ready(client, admin_headers)                 # Einrichtung im Hintergrund abwarten, sonst überschreibt sie den Zustand
    yield pid
    preview_auth._tickets.clear()
    preview_net._addr.clear()


def _open(client, headers, pid, host="vibe.example"):
    return client.post(f"{B}/projects/{pid}/preview/open", headers={**headers, "Host": host}, json={})


@pytest.fixture
def way(monkeypatch):
    """Weg vorbereitet: Netzregel da, nginx-Block da, Container schläft nicht, Adresse bekannt."""
    async def noop(*a, **k): return None
    async def addr(pid): return "10.79.0.9:5173"
    monkeypatch.setattr(preview_net, "open_port", noop)
    monkeypatch.setattr(preview_net, "address", addr)
    monkeypatch.setattr(preview_site, "is_applied", lambda **k: True)
    from backend import idle
    monkeypatch.setattr(idle, "wake", noop)


def _ticket(client, headers, pid):
    r = _open(client, headers, pid)
    assert r.status_code == 200, r.text
    assert r.json()["url"].startswith("https://vibe.example:8444/__vibe_login?t=")
    return r.json()["url"].split("t=", 1)[1]


def test_ticket_ohne_login(client, proj, way):
    assert client.post(f"{B}/projects/{proj}/preview/open", json={}).status_code == 401


def test_ticket_nur_fuer_admins(client, user_headers, proj, way):
    assert _open(client, user_headers, proj).status_code == 403


def test_ticket_fremdes_oder_fehlendes_projekt(client, admin_headers, way, env):  # noqa: F811
    assert _open(client, admin_headers, "gibtsnicht").status_code == 404


def test_ticket_nur_wenn_projekt_bereit(client, admin_headers, proj, way):
    state.set_state(proj, "setting_up")
    assert _open(client, admin_headers, proj).status_code == 409


def test_ticket_einloesen_setzt_cookie_fuer_das_iframe(client, admin_headers, proj, way):
    t = _ticket(client, admin_headers, proj)
    r = client.get(LOGIN, params={"t": t}, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/"
    parts = [x.strip().lower() for x in r.headers["set-cookie"].split(";")]
    assert r.headers["set-cookie"].startswith("hh_vibe_preview=")
    for part in ("httponly", "secure", "samesite=none", "path=/", "max-age=28800"):
        assert part in parts


def test_ticket_nur_einmal(client, admin_headers, proj, way):
    t = _ticket(client, admin_headers, proj)
    assert client.get(LOGIN, params={"t": t}, follow_redirects=False).status_code == 303
    assert client.get(LOGIN, params={"t": t}, follow_redirects=False).status_code == 401


def test_ticket_laeuft_nach_60_sekunden_ab(client, admin_headers, proj, way, monkeypatch):
    t = _ticket(client, admin_headers, proj)
    monkeypatch.setattr(time, "time", lambda: time.monotonic() + 10**10)
    assert client.get(LOGIN, params={"t": t}, follow_redirects=False).status_code == 401


def test_unbekanntes_ticket(client, proj, way):
    assert client.get(LOGIN, params={"t": "x" * 40}, follow_redirects=False).status_code == 401


def _cookie(client, headers, pid):
    t = _ticket(client, headers, pid)
    r = client.get(LOGIN, params={"t": t}, follow_redirects=False)
    return r.headers["set-cookie"].split(";")[0].split("=", 1)[1]


def test_pruefung_ohne_cookie_ist_401(client, proj, way):
    assert client.get(AUTH).status_code == 401


def test_pruefung_mit_cookie_nennt_das_ziel(client, admin_headers, proj, way):
    c = _cookie(client, admin_headers, proj)
    r = client.get(AUTH, cookies={"hh_vibe_preview": c})
    assert r.status_code == 204 and r.headers["x-vibe-up"] == "10.79.0.9:5173"


def test_pruefung_gefaelschtes_cookie(client, admin_headers, proj, way):
    c = _cookie(client, admin_headers, proj)
    body, sig = c.split(".")
    assert client.get(AUTH, cookies={"hh_vibe_preview": body + "." + sig[::-1]}).status_code == 401
    assert client.get(AUTH, cookies={"hh_vibe_preview": "x." * 3}).status_code == 401
    assert client.get(AUTH, cookies={"hh_vibe_preview": "a" * 700}).status_code == 401


def test_pruefung_nach_loeschen_des_projekts(client, admin_headers, proj, way):
    c = _cookie(client, admin_headers, proj)
    state.delete_row(proj)
    assert client.get(AUTH, cookies={"hh_vibe_preview": c}).status_code == 401


def test_pruefung_container_ohne_adresse(client, admin_headers, proj, monkeypatch):
    async def none(pid): return None
    async def noop(*a, **k): return None
    from backend import idle
    monkeypatch.setattr(preview_net, "open_port", noop); monkeypatch.setattr(preview_site, "is_applied", lambda **k: True)
    monkeypatch.setattr(idle, "wake", noop)
    c = _cookie(client, admin_headers, proj)
    monkeypatch.setattr(preview_net, "address", none)
    assert client.get(AUTH, cookies={"hh_vibe_preview": c}).status_code == 401


def test_seltsamer_host_wird_abgelehnt(client, admin_headers, proj, way):
    r = client.post(f"{B}/projects/{proj}/preview/open", headers={**admin_headers, "Host": "a b/c"}, json={})
    assert r.status_code == 400 and r.json()["detail"]["code"] == "vibe_preview_bad_host"
    assert preview_auth._tickets == {}


def test_nginx_block_nicht_angewendet_meldet_klar(client, admin_headers, proj, monkeypatch, way):
    monkeypatch.setattr(preview_site, "is_applied", lambda **k: False)
    monkeypatch.setattr(preview_site, "apply", lambda **k: False)
    r = _open(client, admin_headers, proj)
    assert r.status_code == 503 and r.json()["detail"]["code"] == "vibe_preview_unavailable"


# ---- nginx-Block ----------------------------------------------------------------------------------------------

@pytest.fixture
def conf():
    return preview_site.nginx_conf()


def _loc(conf, head):
    i = conf.index(head)
    return conf[i:conf.index("\n    }", i)]


def test_port_tls_und_nur_heimnetz(conf):
    assert "listen 8444 ssl;" in conf and "listen [::]:8444 ssl;" in conf and "default_server" not in conf
    assert "ssl_certificate     /etc/hydrahive2/tls/hydrahive.crt;" in conf
    for n in ("10.0.0.0/8", "192.168.0.0/16", "100.64.0.0/10", "fd7a:115c:a1e0::/48", "127.0.0.1"):
        assert f"allow {n};" in conf
    assert "deny all;" in conf and "allow 0.0.0.0/0" not in conf


def test_einbetten_nur_von_hydrahive_und_kein_x_frame_options(conf):
    assert "frame-ancestors https://$host;" in conf
    assert "add_header X-Frame-Options" not in conf and "proxy_hide_header X-Frame-Options;" in conf


def test_keine_cookies_zur_vorschau_und_keine_von_ihr(conf):
    loc = _loc(conf, "    location / {")
    assert 'proxy_set_header Cookie "";' in loc and "proxy_hide_header Set-Cookie;" in loc


def test_alles_ausser_login_wird_geprueft_und_ziel_kommt_aus_der_pruefung(conf):
    loc = _loc(conf, "    location / {")
    assert "auth_request /__vibe_auth;" in loc and "proxy_pass http://$vibe_up;" in loc
    assert "auth_request_set $vibe_up $upstream_http_x_vibe_up;" in loc
    assert "auth_request" not in _loc(conf, "    location = /__vibe_login")


def test_weboscket_und_langer_timeout(conf):
    loc = _loc(conf, "    location / {")
    assert "proxy_set_header Upgrade $http_upgrade;" in loc and "proxy_read_timeout 1h;" in loc


def test_zugriffsprotokoll_aus_weil_im_pfad_nichts_geheimes_stehen_soll(conf):
    assert "access_log off;" in conf


def test_csp_erlaubt_nur_eigene_verbindungen(conf):
    assert "connect-src 'self';" in conf and "form-action 'self';" in conf and "object-src 'none';" in conf


class FakeRoot:
    def __init__(self, rc=0): self.rc, self.scripts = rc, []

    def __call__(self, script): self.scripts.append(script); return self.rc, ""


def test_anwenden_schreibt_datei_und_ruft_root_einmal(tmp_path):
    r = FakeRoot()
    assert preview_site.apply(root=r, data_dir=tmp_path) is True
    assert (tmp_path / preview_site.CONF_NAME).read_text() == preview_site.nginx_conf()
    assert len(r.scripts) == 1 and "nginx -t" in r.scripts[0] and ".alt" in r.scripts[0]


def test_anwenden_meldet_fehler_wenn_root_scheitert(tmp_path):
    assert preview_site.apply(root=FakeRoot(rc=1), data_dir=tmp_path) is False


def test_entfernen_raeumt_datei_und_ruft_root(tmp_path):
    (tmp_path / preview_site.CONF_NAME).write_text("x")
    r = FakeRoot()
    preview_site.remove(root=r, data_dir=tmp_path)
    assert not (tmp_path / preview_site.CONF_NAME).exists() and len(r.scripts) == 1


# ---- Weg Server → Container -----------------------------------------------------------------------------------

async def test_eingangsregel_wird_genau_einmal_angelegt(env, monkeypatch):  # noqa: F811
    monkeypatch.setattr(network, "_host_networks", lambda: set())
    monkeypatch.setattr(network, "_host_addresses", lambda: set())
    await network.ensure_network()
    assert await preview_net.is_open() is False
    await preview_net.open_port()
    await preview_net.open_port()
    adds = [c for c in env.calls if c[:4] == ["network", "acl", "rule", "add"] and "ingress" in c]
    assert len(adds) == 1 and "destination_port=5173" in adds[0] and "protocol=tcp" in adds[0]
    assert any(a.startswith("source=") and a.endswith("/32") for a in adds[0])
    assert await preview_net.is_open() is True


async def test_adresse_nur_private_ipv4(env, monkeypatch):  # noqa: F811
    preview_net._addr.clear()
    env.containers[container.name_for("p1")] = {"network": "hhvibe0"}

    async def run(*args, timeout=60.0, input_bytes=None):
        return 0, "10.79.0.7 (eth0)\n", ""
    monkeypatch.setattr(preview_net.incus, "run", run)
    assert await preview_net.address("p1") == "10.79.0.7:5173"
    preview_net._addr.clear()

    async def oeffentlich(*args, timeout=60.0, input_bytes=None):
        return 0, "8.8.8.8 (eth0)\n", ""
    monkeypatch.setattr(preview_net.incus, "run", oeffentlich)
    assert await preview_net.address("p1") is None


async def test_adresse_ohne_ausgabe_oder_fehler(env, monkeypatch):  # noqa: F811
    preview_net._addr.clear()

    async def leer(*args, timeout=60.0, input_bytes=None):
        return 0, "", ""

    async def kaputt(*args, timeout=60.0, input_bytes=None):
        return 1, "10.79.0.7", "x"
    monkeypatch.setattr(preview_net.incus, "run", leer)
    assert await preview_net.address("p2") is None
    monkeypatch.setattr(preview_net.incus, "run", kaputt)
    assert await preview_net.address("p2") is None


# ---- Aufräumen: letztes Projekt weg → nginx-Block weg -----------------------------------------------------------

@pytest.fixture
def fake_root(monkeypatch, tmp_path):
    """Nie echtes sudo in Tests: root() und das Datenverzeichnis werden ersetzt."""
    r = FakeRoot()
    monkeypatch.setattr(preview_site, "root", r)
    monkeypatch.setattr(preview_site, "data_dir", lambda: tmp_path)
    (tmp_path / preview_site.CONF_NAME).write_text("x")
    return r


def test_letztes_projekt_loeschen_entfernt_den_nginx_block(client, admin_headers, proj, fake_root):
    assert client.delete(f"{B}/projects/{proj}", headers=admin_headers).status_code == 200
    assert len(fake_root.scripts) == 1 and "rm -f" in fake_root.scripts[0] and preview_site.SITE in fake_root.scripts[0]


def test_nicht_letztes_projekt_loeschen_laesst_den_block_stehen(client, admin_headers, proj, fake_root, monkeypatch):
    zweites = _create(client, admin_headers, name="Zweite").json()["project_id"]
    _ready(client, admin_headers)
    assert client.delete(f"{B}/projects/{proj}", headers=admin_headers).status_code == 200
    assert fake_root.scripts == []
    assert zweites


def test_fehler_beim_entfernen_des_blocks_stoppt_das_loeschen_nicht(client, admin_headers, proj, monkeypatch, tmp_path):
    def boom(script): raise OSError("kein sudo")
    monkeypatch.setattr(preview_site, "root", boom)
    monkeypatch.setattr(preview_site, "data_dir", lambda: tmp_path)
    assert client.delete(f"{B}/projects/{proj}", headers=admin_headers).status_code == 200
    assert state.get_row(proj) is None
