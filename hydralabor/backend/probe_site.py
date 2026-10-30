"""L3 (PLAN-L3.md Baustein 3, Weg A): nginx-Block der Durchreiche :8443 – Muster radiostream listener_site/apply.

- Nur Heimnetz/Tailscale (wie Radiostream-Hörerseite „home“), TLS mit dem Zertifikat des Servers.
- Jede Anfrage prüft nginx per auth_request gegen das Modul (Cookie hh_labor_probe, probe_auth.py); ein gültiges
  Ergebnis merkt sich nginx 30 s je Cookie (sonst bremst der Geräte-Weg des Kerns: 240 Anfragen/min je Adresse).
- `/__labor_login` (Ticket einlösen) ist der einzige Weg ohne Prüfung.
- An die Probe gehen keine Cookies (der Kern nutzt keine; Cookies trennen nicht nach Port – sonst sähe Labor-Code
  hh_labor_probe und hh_agentlink). Den Bearer-Kopf braucht die Probe selbst (eigene Anmeldung, eigener Ursprung).
- Antworten der Probe ohne `Set-Cookie` (ein Cookie von :8443 bekäme auch das echte HydraHive). Rest: Labor-JS kann
  per document.cookie Cookies setzen – das echte HydraHive meldet per Bearer an (kein Cookie), schlimmstenfalls
  ist ein Dashboard-/Probe-Cookie überdeckt (neu öffnen hilft).
- CSP `connect-src 'self'`/`form-action 'self'`: Code aus dem Labor schickt von :8443 nichts an das echte HydraHive.
  Eigene CSP der Probe kann das nicht lockern (mehrere CSP gelten alle). Token des echten HydraHive liegt im
  sessionStorage seines Ursprungs (:443) – :8443 ist ein anderer Ursprung.
Der root-Befehl enthält nur feste Pfade; der Block kommt aus einer Datei. `nginx -t` lehnt ab → alte Fassung zurück.
"""
from __future__ import annotations

import ipaddress
import os
import subprocess
from collections.abc import Callable
from pathlib import Path

PORT = 8443
UPSTREAM_PORT = 8001
SITE = "hydrahive-labor-probe"
AVAILABLE = f"/etc/nginx/sites-available/{SITE}"
ENABLED = f"/etc/nginx/sites-enabled/{SITE}"
CACHE = "/var/cache/hydrahive-labor-probe"
CONF_NAME = "nginx-probe.conf"
HOME_NETS = ("127.0.0.1", "::1", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "100.64.0.0/10",
             "fc00::/7", "fe80::/10", "fd7a:115c:a1e0::/48")
_DEV = "http://127.0.0.1:8001/api/module-device/hydralabor/probe"
_CSP = ("default-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; "
        "script-src 'self' 'unsafe-eval' 'wasm-unsafe-eval'; connect-src 'self'; font-src 'self' data:; "
        "media-src 'self' blob:; object-src 'none'; frame-ancestors 'none'; base-uri 'self'; form-action 'self';")
_HINT = ("<html><body><p>Bitte im Hydra-Labor „Probe öffnen“ wählen.</p>"
         "<p>Please choose “Open preview” in the Hydra lab.</p></body></html>")
Root = Callable[[str], tuple[int, str]]


def _check_ip(ip: str) -> str:
    """Nur eine private IPv4 (ipaddress lehnt Leerzeichen, Zeilenumbruch, führende Nullen und Kurzformen ab)."""
    try:
        addr = ipaddress.IPv4Address(ip)
    except ValueError:
        raise ValueError("labor_probe_bad_address") from None
    if not addr.is_private:
        raise ValueError("labor_probe_bad_address")
    return ip


def nginx_conf(ip: str) -> str:
    up = f"http://{_check_ip(ip)}:{UPSTREAM_PORT}"
    allow = "".join(f"    allow {n};\n" for n in HOME_NETS)
    return f"""# Erzeugt von HydraHive Hydra-Labor – nicht von Hand ändern.
map $http_upgrade $hh_labor_conn {{
    default upgrade;
    '' close;
}}
proxy_cache_path {CACHE} levels=1 keys_zone=hh_labor_auth:1m max_size=5m inactive=10m use_temp_path=off;

server {{
    listen {PORT} ssl;
    listen [::]:{PORT} ssl;
    server_name _;
    server_tokens off;
    ssl_certificate     /etc/hydrahive2/tls/hydrahive.crt;
    ssl_certificate_key /etc/hydrahive2/tls/hydrahive.key;
    ssl_protocols       TLSv1.2 TLSv1.3;
{allow}    deny all;

    add_header Content-Security-Policy "{_CSP}" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer" always;

    location = /__labor_auth {{
        internal;
        proxy_pass {_DEV}/auth;
        proxy_pass_request_body off;
        proxy_set_header Content-Length "";
        proxy_set_header Cookie $http_cookie;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_cache hh_labor_auth;
        proxy_cache_key $cookie_hh_labor_probe;
        proxy_cache_valid 204 30s;
    }}

    location = /__labor_login {{
        proxy_pass {_DEV}/login;
        proxy_pass_request_body off;
        proxy_set_header Content-Length "";
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $remote_addr;
    }}

    location @labor_login {{
        default_type text/html;
        return 401 "{_HINT}";
    }}

    location / {{
        auth_request /__labor_auth;
        error_page 401 = @labor_login;
        proxy_pass {up};
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $hh_labor_conn;
        proxy_set_header Cookie "";
        proxy_hide_header Set-Cookie;
        proxy_buffering off;
        proxy_read_timeout 1h;
        client_max_body_size 200m;
    }}
}}
"""


def root(script: str) -> tuple[int, str]:
    """Wie radiostream control._root: `sudo -n bash` (Regel des Installers), nur feste Texte im Befehl."""
    cmd = ["bash", "-c", script] if os.getuid() == 0 else ["sudo", "-n", "bash", "-c", script]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60, check=False)
    return r.returncode, (r.stdout + r.stderr).strip()


def apply(ip: str, *, root: Root, data_dir: Path) -> bool:
    conf = data_dir / CONF_NAME
    data_dir.mkdir(parents=True, exist_ok=True)
    conf.write_text(nginx_conf(ip))
    rc, _ = root(
        f"install -d -m 700 {CACHE}\n"
        f"if [ -e {AVAILABLE} ]; then cp -a {AVAILABLE} {AVAILABLE}.alt; else rm -f {AVAILABLE}.alt; fi\n"
        f"install -m 644 {conf} {AVAILABLE} && ln -sf {AVAILABLE} {ENABLED}\n"
        f"if nginx -t >/dev/null 2>&1; then rm -f {AVAILABLE}.alt; systemctl reload nginx; exit 0; fi\n"
        f"if [ -e {AVAILABLE}.alt ]; then mv -f {AVAILABLE}.alt {AVAILABLE}; else rm -f {ENABLED} {AVAILABLE}; fi\n"
        f"nginx -t >/dev/null 2>&1 && systemctl reload nginx\nexit 1")
    return rc == 0


def remove(*, root: Root, data_dir: Path) -> None:
    (data_dir / CONF_NAME).unlink(missing_ok=True)
    root(f"if [ -e {ENABLED} ] || [ -e {AVAILABLE} ]; then rm -f {ENABLED} {AVAILABLE}\n"
         f"nginx -t >/dev/null 2>&1 && systemctl reload nginx; fi\nrm -rf {CACHE}; exit 0")
