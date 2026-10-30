"""Hydra-Labor L3: nginx-Block der Durchreiche :8443 (Inhalt) und Anwenden/Entfernen mit Rücknahme (root als Attrappe)."""
from __future__ import annotations

import re

import pytest
from backend import probe_site

IP = "10.77.0.5"


@pytest.fixture
def conf():
    return probe_site.nginx_conf(IP)


def _loc(conf: str, head: str) -> str:
    i = conf.index(head)
    return conf[i:conf.index("\n    }", i)]


def test_port_und_tls(conf):
    assert "listen 8443 ssl;" in conf and "listen [::]:8443 ssl;" in conf
    assert "ssl_certificate     /etc/hydrahive2/tls/hydrahive.crt;" in conf
    assert "ssl_certificate_key /etc/hydrahive2/tls/hydrahive.key;" in conf
    assert "default_server" not in conf


def test_nur_heimnetz(conf):
    for n in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "100.64.0.0/10", "fd7a:115c:a1e0::/48", "127.0.0.1"):
        assert f"allow {n};" in conf
    assert conf.index("deny all;") > max(conf.index(f"allow {n};") for n in ("10.0.0.0/8", "fd7a:115c:a1e0::/48"))
    assert "0.0.0.0/0" not in conf


def test_pruefung_vor_der_probe(conf):
    root = _loc(conf, "location / {")
    assert "auth_request /__labor_auth;" in root
    assert f"proxy_pass http://{IP}:8001;" in root
    assert "error_page 401 = @labor_login;" in root


def test_pruefung_geht_an_den_geraete_weg(conf):
    a = _loc(conf, "location = /__labor_auth {")
    assert "internal;" in a
    assert "proxy_pass http://127.0.0.1:8001/api/module-device/hydralabor/probe/auth;" in a
    assert "proxy_pass_request_body off;" in a
    assert 'proxy_set_header Content-Length "";' in a


def test_login_weg_ohne_pruefung_aber_nur_dieser(conf):
    a = _loc(conf, "location = /__labor_login {")
    assert "proxy_pass http://127.0.0.1:8001/api/module-device/hydralabor/probe/login;" in a
    assert "auth_request" not in a
    assert conf.count("proxy_pass http://127.0.0.1:8001") == 2


def test_keine_cookies_an_die_probe(conf):
    """Der Kern nutzt keine Cookies (Login per Bearer im sessionStorage, je Ursprung getrennt). Cookies trennen nicht
    nach Port – ohne Leeren sähe Labor-Code hh_labor_probe und hh_agentlink."""
    root = _loc(conf, "location / {")
    assert 'proxy_set_header Cookie "";' in root
    assert "Authorization" not in root                       # Bearer der Probe selbst muss durch
    assert "X-Forwarded-For" not in root and "X-Real-IP" not in root


def test_probe_setzt_keine_cookies(conf):
    """Cookies trennen nicht nach Port: ein Cookie von :8443 bekäme auch das echte HydraHive (:443)."""
    assert "proxy_hide_header Set-Cookie;" in _loc(conf, "location / {")


def test_bremse_je_browser_adresse(conf):
    for head in ("location = /__labor_auth {", "location = /__labor_login {"):
        assert "proxy_set_header X-Forwarded-For $remote_addr;" in _loc(conf, head)


def test_pruefung_wird_kurz_gemerkt(conf):
    assert re.search(r"proxy_cache_path /var/cache/hydrahive-labor-probe levels=1 keys_zone=hh_labor_auth:1m "
                     r"max_size=5m inactive=10m use_temp_path=off;", conf)
    a = _loc(conf, "location = /__labor_auth {")
    assert "proxy_cache hh_labor_auth;" in a
    assert "proxy_cache_key $cookie_hh_labor_probe;" in a
    assert "proxy_cache_valid 204 30s;" in a
    assert "proxy_cache_valid 401" not in a and "proxy_cache_valid any" not in a
    assert "proxy_set_header Cookie $http_cookie;" in a


def test_csp_schuetzt_das_echte_hydrahive(conf):
    m = re.search(r'add_header Content-Security-Policy "([^"]+)" always;', conf)
    csp = m.group(1)
    for d in ("default-src 'self'", "connect-src 'self';", "form-action 'self'", "frame-ancestors 'none'",
              "base-uri 'self'", "object-src 'none'"):
        assert d in csp
    assert "wss:" not in csp and "https:" not in csp and "*" not in csp


def test_hinweis_ohne_anmeldung(conf):
    a = _loc(conf, "location @labor_login {")
    assert "return 401" in a and "Probe öffnen" in a


def test_websocket(conf):
    root = _loc(conf, "location / {")
    assert "proxy_http_version 1.1;" in root
    assert "proxy_set_header Upgrade $http_upgrade;" in root
    assert 'proxy_set_header Connection "upgrade";' not in root          # nur bei Upgrade – siehe map
    assert "proxy_set_header Connection $hh_labor_conn;" in root
    assert re.search(r"map \$http_upgrade \$hh_labor_conn \{\s+default upgrade;\s+'' close;\s+\}", conf)


def test_kopfzeilen(conf):
    assert 'add_header X-Frame-Options "DENY" always;' in conf
    assert 'add_header X-Content-Type-Options "nosniff" always;' in conf
    assert 'add_header Referrer-Policy "no-referrer" always;' in conf
    assert "server_tokens off;" in conf


def test_grosse_dateien_und_lange_antworten(conf):
    root = _loc(conf, "location / {")
    assert "client_max_body_size 200m;" in root
    assert "proxy_read_timeout 1h;" in root
    assert "proxy_buffering off;" in root


@pytest.mark.parametrize("ip", ["", "10.77.0", "10.77.0.256", "10.77.0.5;", "10.77.0.5 x", "fd00::1", "a.b.c.d",
                                "10.77.0.5\n", "010.77.0.5", "8.8.8.8", " 10.77.0.5", None])
def test_nur_echte_ipv4(ip):
    with pytest.raises(ValueError, match="^labor_probe_bad_address$"):
        probe_site.nginx_conf(ip)


# --- anwenden / entfernen --------------------------------------------------------------------------------------------

class Root:
    def __init__(self, rc=0):
        self.calls: list[str] = []
        self.rc = rc

    def __call__(self, script: str):
        self.calls.append(script)
        return self.rc, ""


def test_anwenden_schreibt_datei_und_laedt(tmp_path):
    root = Root()
    assert probe_site.apply(IP, root=root, data_dir=tmp_path)
    f = tmp_path / "nginx-probe.conf"
    assert f.read_text() == probe_site.nginx_conf(IP)
    s = root.calls[0]
    assert f"install -m 644 {f} /etc/nginx/sites-available/hydrahive-labor-probe" in s
    assert "ln -sf /etc/nginx/sites-available/hydrahive-labor-probe /etc/nginx/sites-enabled/hydrahive-labor-probe" in s
    assert "nginx -t" in s and "systemctl reload nginx" in s
    assert s.index("cp -a") < s.index("install -m 644") < s.index("nginx -t")
    assert "install -d -m 700 /var/cache/hydrahive-labor-probe" in s
    assert IP not in s                                        # nie Text aus der Laufzeit im root-Befehl


def test_anwenden_fehler(tmp_path):
    assert probe_site.apply(IP, root=Root(rc=1), data_dir=tmp_path) is False


def test_ruecknahme_im_befehl(tmp_path):
    root = Root()
    probe_site.apply(IP, root=root, data_dir=tmp_path)
    s = root.calls[0]
    assert "mv -f /etc/nginx/sites-available/hydrahive-labor-probe.alt /etc/nginx/sites-available/hydrahive-labor-probe" in s
    assert "rm -f /etc/nginx/sites-enabled/hydrahive-labor-probe /etc/nginx/sites-available/hydrahive-labor-probe" in s
    assert s.rstrip().endswith("exit 1")


def test_entfernen(tmp_path):
    root = Root()
    (tmp_path / "nginx-probe.conf").write_text("x")
    probe_site.remove(root=root, data_dir=tmp_path)
    assert not (tmp_path / "nginx-probe.conf").exists()
    s = root.calls[0]
    assert "rm -f /etc/nginx/sites-enabled/hydrahive-labor-probe /etc/nginx/sites-available/hydrahive-labor-probe" in s
    assert "systemctl reload nginx" in s
    assert "rm -rf /var/cache/hydrahive-labor-probe" in s


def test_entfernen_nur_eigene_datei(tmp_path):
    root = Root()
    probe_site.remove(root=root, data_dir=tmp_path)
    s = root.calls[0]
    for other in ("hydrahive2", "hydrahive-radiostream", "gitea", "default", "*"):
        assert f"sites-enabled/{other} " not in s and f"sites-available/{other} " not in s


def test_root_ohne_sudo_als_root(monkeypatch):
    seen = {}
    monkeypatch.setattr(probe_site.os, "getuid", lambda: 0)
    monkeypatch.setattr(probe_site.subprocess, "run", lambda cmd, **kw: seen.setdefault("cmd", cmd) and type(
        "R", (), {"returncode": 0, "stdout": "", "stderr": ""})())
    probe_site.root("true")
    assert seen["cmd"] == ["bash", "-c", "true"]


def test_root_mit_sudo(monkeypatch):
    seen = {}
    monkeypatch.setattr(probe_site.os, "getuid", lambda: 1000)
    monkeypatch.setattr(probe_site.subprocess, "run", lambda cmd, **kw: seen.setdefault("cmd", cmd) and type(
        "R", (), {"returncode": 0, "stdout": "", "stderr": ""})())
    probe_site.root("true")
    assert seen["cmd"] == ["sudo", "-n", "bash", "-c", "true"]
