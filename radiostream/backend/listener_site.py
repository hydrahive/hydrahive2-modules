"""Hörer-Seite (SPEC.md „Hörer-Seite“): eigener nginx-Block auf eigenem Port und statische Seite.

Nur drei Wege: `/` (Seite), `/stream` (Icecast-Mount), `/jetzt` (fertige JSON-Datei von Liquidsoap). Kein Weg zu
HydraHive. Nichts aus den Einstellungen außer Port und Zahlen landet im nginx-Block – der Sendername steht nur in der
statischen Seite (HTML-maskiert). Die Seite hat keine Fremd-Adressen und kein Inline-Skript (CSP default-src 'self').
"""
from __future__ import annotations

from html import escape

from . import listener_page
from .service_files import ICECAST_PORT, MOUNT

HOME_NETS = ("127.0.0.1", "::1", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "100.64.0.0/10",
             "fc00::/7", "fe80::/10", "fd7a:115c:a1e0::/48")
PER_IP = 3
_CSP = ("default-src 'self'; media-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; "
        "connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")


def _headers(indent: str) -> str:
    """Sicherheits-Kopfzeilen. Je Location neu, sobald dort ein eigenes add_header steht (nginx erbt dann nicht)."""
    return "".join(f"{indent}add_header {h} always;\n" for h in (
        f'Content-Security-Policy "{_CSP}"', 'X-Content-Type-Options "nosniff"', 'Referrer-Policy "no-referrer"',
        'X-Frame-Options "DENY"'))


def nginx_conf(st: dict, *, web_dir: str) -> str:
    if st["reach"] == "off":
        return ""
    port = int(st["listen_port"])
    total = int(st["max_listeners"]) * 2           # Seite + Stream je Hörer; die harte Grenze setzt Icecast
    access = ""
    if st["reach"] == "home":
        access = "".join(f"    allow {n};\n" for n in HOME_NETS) + "    deny all;\n"
    upstream = f"http://127.0.0.1:{ICECAST_PORT}{MOUNT}"
    stream = (f"proxy_pass {upstream};\n        proxy_set_header Host 127.0.0.1;\n        proxy_buffering off;\n"
              "        proxy_read_timeout 1h;\n        proxy_http_version 1.1;")
    static = "\n".join(f"    location = /{f} {{\n        alias {web_dir}/{f};\n    }}"
                       for f in ("index.html", "radio.css", "radio.js"))
    return f"""# Erzeugt von HydraHive Radiostream – nicht von Hand ändern.
limit_conn_zone $binary_remote_addr zone=radiostream_ip:2m;
limit_conn_zone $server_name zone=radiostream_all:1m;

server {{
    listen {port};
    listen [::]:{port};
    server_name _;
    server_tokens off;
    access_log off;
{access}    limit_conn radiostream_ip {PER_IP};
    limit_conn radiostream_all {total};
{_headers("    ")}
    location = / {{
        root {web_dir};
        try_files /index.html =404;
    }}
{static}
    location = /stream {{
        {stream}
    }}
    location = /stream.mp3 {{
        {stream}
    }}
    location = /stream.m3u {{
        default_type audio/x-mpegurl;
        return 200 "#EXTM3U\\n$scheme://$http_host/stream.mp3\\n";
    }}
    location = /jetzt {{
        alias {web_dir}/jetzt.json;
        default_type application/json;
        add_header Cache-Control "no-store" always;
{_headers("        ")}    }}
    location / {{
        return 404;
    }}
}}
"""


def page_files(st: dict) -> dict[str, str]:
    name, sub = escape(st["name"]), escape(st.get("subtitle") or "")
    return {"index.html": listener_page.HTML.replace("{{NAME}}", name).replace("{{SUBTITLE}}", sub),
            "radio.css": listener_page.CSS, "radio.js": listener_page.JS}
