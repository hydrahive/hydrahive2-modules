"""Hörer-Seite (SPEC.md „Hörer-Seite“, PLAN-E2.md Punkt 5): eigener nginx-Block, nur drei Wege, keine Fremd-Dateien.

Geprüft wird der erzeugte Text. Ob nginx ihn annimmt (`nginx -t`), prüft die Probe auf hydratest.
"""
from __future__ import annotations

import re

import pytest
from backend import listener_site as ls
from backend import service_files as sf

_ST = {"name": "Molke FM", "subtitle": "rund um die Uhr", "listen_port": 8800, "reach": "all", "max_listeners": 50}


def _conf(**kw) -> str:
    return ls.nginx_conf({**_ST, **kw}, web_dir="/var/www/radio")


def _locations(conf: str) -> list[str]:
    return re.findall(r"^\s*location\s+([^{]+?)\s*\{", conf, re.MULTILINE)


def test_nur_die_drei_wege_und_sonst_404():
    c = _conf()
    assert sorted(_locations(c)) == sorted(["= /", "= /index.html", "= /radio.css", "= /radio.js",
                                            "= /stream", "= /stream.mp3", "= /stream.m3u", "= /jetzt", "/"])
    rest = c[c.index("location / {"):]
    assert "return 404;" in rest[:rest.index("}")]


def test_kein_weg_zu_hydrahive_oder_icecast_admin():
    c = _conf()
    assert "8001" not in c and "/api" not in c and "/admin" not in c
    proxies = re.findall(r"proxy_pass\s+([^;]+);", c)
    assert proxies == [f"http://127.0.0.1:{sf.ICECAST_PORT}{sf.MOUNT}"] * 2


def test_lauscht_auf_dem_eingestellten_port_ipv4_und_ipv6():
    c = _conf(listen_port=8899)
    assert "listen 8899;" in c and "listen [::]:8899;" in c
    assert "8800" not in c


def test_alle_erreichbar_ohne_adressregeln():
    c = _conf(reach="all")
    assert "allow " not in c and "deny all;" not in c


def test_heimnetz_nur_private_tailscale_und_lokal():
    c = _conf(reach="home")
    allow = re.findall(r"allow\s+([^;]+);", c)
    assert sorted(allow) == sorted(["127.0.0.1", "::1", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16",
                                    "100.64.0.0/10", "fc00::/7", "fe80::/10", "fd7a:115c:a1e0::/48"])
    assert "deny all;" in c
    assert c.index("allow 127.0.0.1;") < c.index("deny all;")


def test_aus_ergibt_keinen_block():
    assert ls.nginx_conf({**_ST, "reach": "off"}, web_dir="/x") == ""


def test_grenzen_je_adresse_und_insgesamt():
    c = _conf(max_listeners=20)
    assert re.search(r"limit_conn_zone \$binary_remote_addr zone=radiostream_ip:\d+m;", c)
    assert "limit_conn radiostream_ip 3;" in c
    assert re.search(r"limit_conn_zone \$server_name zone=radiostream_all:\d+m;", c)
    assert "limit_conn radiostream_all 40;" in c


def test_sicherheits_kopfzeilen():
    c = _conf()
    assert "add_header Content-Security-Policy \"default-src 'self'; media-src 'self'; img-src 'self' data:;" \
           " style-src 'self'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none';" \
           " form-action 'none'\" always;" in c
    for h in ('X-Content-Type-Options "nosniff"', 'Referrer-Policy "no-referrer"', 'X-Frame-Options "DENY"'):
        assert f"add_header {h} always;" in c
    assert "server_tokens off;" in c


def test_stream_ohne_puffer_und_ohne_kopfzeilen_von_innen():
    c = _conf()
    block = c[c.index("location = /stream {"):]
    block = block[:block.index("}")]
    assert "proxy_buffering off;" in block
    assert "proxy_set_header Host 127.0.0.1;" in block


def test_jetzt_ist_die_fertige_datei_ohne_cache():
    c = _conf()
    block = c[c.index("location = /jetzt {"):]
    block = block[:block.index("}")]
    assert "alias /var/www/radio/jetzt.json;" in block
    assert "default_type application/json;" in block
    assert "proxy_pass" not in block
    assert 'add_header Cache-Control "no-store" always;' in block
    # eigenes add_header → nginx erbt die Sicherheits-Kopfzeilen nicht, sie müssen hier noch einmal stehen
    for h in ("Content-Security-Policy", "X-Content-Type-Options", "Referrer-Policy", "X-Frame-Options"):
        assert f"add_header {h} " in block


def test_m3u_zeigt_auf_den_eigenen_stream():
    c = _conf()
    block = c[c.index("location = /stream.m3u {"):]
    block = block[:block.index("}")]
    assert "default_type audio/x-mpegurl;" in block
    assert "return 200 \"#EXTM3U\\n$scheme://$http_host/stream.mp3\\n\";" in block


@pytest.mark.parametrize("name", ['Böse"; return 302 http://x; #', "a\nb", "a;b{c}d$e"])
def test_sendername_kommt_nicht_in_den_nginx_block(name):
    c = _conf(name=name)
    assert name not in c and "302" not in c


def test_seite_ohne_fremde_adressen_und_mit_namen_maskiert():
    files = ls.page_files({**_ST, "name": "<script>alert(1)</script> & Co", "subtitle": "Unter\"titel"})
    assert set(files) == {"index.html", "radio.css", "radio.js"}
    html = files["index.html"]
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt; &amp; Co" in html
    assert "Unter&quot;titel" in html
    for text in files.values():
        assert not re.search(r"(?i)\b(https?:)?//[a-z0-9]", text.replace("$scheme://", ""))
    assert '<script src="radio.js" defer></script>' in html
    assert '<link rel="stylesheet" href="radio.css">' in html
    assert "<script>" not in html and " style=" not in html and " on" + "click=" not in html


def test_seite_spielt_stream_und_fragt_jetzt_alle_15_sekunden():
    files = ls.page_files(_ST)
    assert 'src="stream.mp3"' in files["index.html"] or "'stream.mp3'" in files["radio.js"]
    assert "fetch('jetzt'" in files["radio.js"] and "15000" in files["radio.js"]
    assert 'href="stream.m3u"' in files["index.html"]
    assert "innerHTML" not in files["radio.js"]
    assert '<meta name="viewport" content="width=device-width, initial-scale=1">' in files["index.html"]


def test_startseite_ueber_try_files_nicht_alias():
    """alias bei „location = /“ hängt index.html noch einmal an (hydratest 29.10.: 500)."""
    c = _conf()
    block = c[c.index("location = / {"):]
    block = block[:block.index("}")]
    assert "root /var/www/radio;" in block and "try_files /index.html =404;" in block and "alias" not in block
