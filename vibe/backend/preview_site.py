"""nginx-Block der Vorschau-Durchreiche :8444 (PLAN-V1.md Entscheidung 8; Muster hydralabor probe_site.py).

- Nur Heimnetz/Tailscale, TLS mit dem Zertifikat des Servers. Eigener Port, damit der Code des Agenten nie im
  Ursprung von HydraHive läuft (anderer Ursprung = kein Zugriff auf dessen sessionStorage).
- Jede Anfrage prüft nginx per auth_request gegen das Modul (Cookie hh_vibe_preview). Das Modul antwortet 204 und
  nennt in `X-Vibe-Up` das Ziel (`ip:5173` des Containers dieses Projekts). Ein gültiges Ergebnis merkt sich nginx 20 s.
- An die Vorschau gehen keine Cookies, von ihr kommt kein Set-Cookie (Cookies trennen nicht nach Port).
- Einbetten nur von der Adresse, unter der der Admin HydraHive nutzt (`frame-ancestors https://$host`), kein
  X-Frame-Options. Der root-Befehl enthält nur feste Pfade; `nginx -t` lehnt ab → alte Fassung zurück.
"""
from __future__ import annotations

import ipaddress
import os
import subprocess
from collections.abc import Callable
from pathlib import Path

PORT = 8444
UPSTREAM_PORT = 8001
SITE = "hydrahive-vibe-preview"
AVAILABLE = f"/etc/nginx/sites-available/{SITE}"
ENABLED = f"/etc/nginx/sites-enabled/{SITE}"
CACHE = "/var/cache/hydrahive-vibe-preview"
CONF_NAME = "nginx-preview.conf"
HOME_NETS = ("127.0.0.1", "::1", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "100.64.0.0/10",
             "fc00::/7", "fe80::/10", "fd7a:115c:a1e0::/48")
_DEV = f"http://127.0.0.1:{UPSTREAM_PORT}/api/module-device/vibe/preview"
# Dev-Server (Vite) braucht Inline-Skripte (React-Refresh) und eval-freie Module; Verbindungen nur zu sich selbst.
_CSP = ("default-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; "
        "script-src 'self' 'unsafe-inline'; connect-src 'self'; font-src 'self' data:; media-src 'self' blob:; "
        "object-src 'none'; frame-ancestors https://$host; base-uri 'self'; form-action 'self';")
_HINT = ("<html><body><p>Bitte in Vibe ein Projekt öffnen.</p><p>Please open a project in Vibe.</p></body></html>")
Root = Callable[[str], tuple[int, str]]


def _check_ip(ip: str) -> str:
    try:
        ipaddress.IPv4Address(ip)
    except ValueError:
        raise ValueError("vibe_preview_bad_address") from None
    return ip


def nginx_conf() -> str:
    allow = "".join(f"    allow {n};\n" for n in HOME_NETS)
    return f"""# Erzeugt von HydraHive Vibe – nicht von Hand ändern.
map $http_upgrade $hh_vibe_conn {{
    default upgrade;
    '' close;
}}
proxy_cache_path {CACHE} levels=1 keys_zone=hh_vibe_auth:1m max_size=5m inactive=10m use_temp_path=off;

server {{
    listen {PORT} ssl;
    listen [::]:{PORT} ssl;
    server_name _;
    server_tokens off;
    ssl_certificate     /etc/hydrahive2/tls/hydrahive.crt;
    ssl_certificate_key /etc/hydrahive2/tls/hydrahive.key;
    ssl_protocols       TLSv1.2 TLSv1.3;
{allow}    deny all;
    access_log off;

    add_header Content-Security-Policy "{_CSP}" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer" always;

    location = /__vibe_auth {{
        internal;
        proxy_pass {_DEV}/auth;
        proxy_pass_request_body off;
        proxy_set_header Content-Length "";
        proxy_set_header Cookie $http_cookie;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_cache hh_vibe_auth;
        proxy_cache_key $cookie_hh_vibe_preview;
        proxy_cache_valid 204 20s;
    }}

    location = /__vibe_login {{
        proxy_pass {_DEV}/login;
        proxy_pass_request_body off;
        proxy_set_header Content-Length "";
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $remote_addr;
    }}

    location @vibe_login {{
        default_type text/html;
        return 401 "{_HINT}";
    }}

    location / {{
        auth_request /__vibe_auth;
        auth_request_set $vibe_up $upstream_http_x_vibe_up;
        error_page 401 = @vibe_login;
        proxy_pass http://$vibe_up;
        proxy_http_version 1.1;
        proxy_set_header Host $http_host;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $hh_vibe_conn;
        proxy_set_header Cookie "";
        proxy_hide_header Set-Cookie;
        proxy_hide_header X-Frame-Options;
        proxy_buffering off;
        proxy_read_timeout 1h;
    }}
}}
"""


def root(script: str) -> tuple[int, str]:
    """Wie hydralabor probe_site.root: `sudo -n bash` (Regel des Installers), nur feste Texte im Befehl."""
    cmd = ["bash", "-c", script] if os.getuid() == 0 else ["sudo", "-n", "bash", "-c", script]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60, check=False)
    return r.returncode, (r.stdout + r.stderr).strip()


def is_applied(*, data_dir: Path) -> bool:
    """Der Block liegt schon und ist der aktuelle (sonst neu schreiben)."""
    conf = data_dir / CONF_NAME
    return conf.exists() and conf.read_text() == nginx_conf() and Path(ENABLED).exists()


def apply(*, root: Root, data_dir: Path) -> bool:
    conf = data_dir / CONF_NAME
    data_dir.mkdir(parents=True, exist_ok=True)
    conf.write_text(nginx_conf())
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
