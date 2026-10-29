"""Zuspielung an Liquidsoap (PLAN-E2.md „Zuspielung“): nur von 127.0.0.1 und nur mit Feed-Schlüssel.

Der Schlüssel liegt in /etc/hydrahive2/radiostream/secrets.env (Test: eigene Datei). Er öffnet nichts anderes als
/feed/*, steht in keiner Antwort und in keinem Log.
"""
from __future__ import annotations

import logging

import pytest
from backend import feed_auth, rotation, scanner
from conftest import MOD_PREFIX as P
from test_routes import _configure, _fill

KEY = "feed-schluessel-123456789012345678901234"


@pytest.fixture
def feed_key(tmp_path, monkeypatch):
    f = tmp_path / "secrets.env"
    f.write_text(f"RADIOSTREAM_FEED_KEY={KEY}\nRADIOSTREAM_SOURCE_PASSWORD=quelle\n")
    monkeypatch.setattr(feed_auth, "SECRETS_FILE", f)
    return KEY


@pytest.fixture
def library(client, admin_headers, safe, fake_share, feed_key):
    _configure(client, admin_headers, safe)
    _fill(fake_share)
    scanner.run_scan()
    return fake_share


def _h(key=KEY):
    return {"X-Radiostream-Feed": key}


def test_naechster_titel_mit_schluessel(client, library):
    r = client.get(f"{P}/feed/next", headers=_h())
    assert r.status_code == 200
    body = r.text.strip()
    assert body.startswith("annotate:") and f"{P}/feed/file/" in body
    assert KEY not in body                                       # Liquidsoap schickt ihn selbst als Kopfzeile


def test_naechster_titel_wird_als_gespielt_eingetragen(client, library):
    client.get(f"{P}/feed/next", headers=_h())
    assert len(rotation.recent(limit=5)) == 1


def test_titel_kommt_mit_kuenstler_und_titel(client, library):
    body = client.get(f"{P}/feed/next", headers=_h()).text
    assert 'artist="' in body and 'title="' in body


@pytest.mark.parametrize("key", ["", "falsch", KEY[:-1], KEY + "x"])
def test_ohne_richtigen_schluessel_403(client, library, key):
    hdr = _h(key) if key else {}
    for path in ("/feed/next", "/feed/file/irgendwas"):
        r = client.get(f"{P}{path}", headers=hdr)
        assert r.status_code == 403 and r.json()["detail"]["code"] == "radiostream_feed_forbidden"
    assert rotation.recent(limit=5) == []


def test_ohne_schluesseldatei_403(client, library, monkeypatch, tmp_path):
    monkeypatch.setattr(feed_auth, "SECRETS_FILE", tmp_path / "gibt-es-nicht.env")
    assert client.get(f"{P}/feed/next", headers=_h()).status_code == 403


def test_nur_von_127_0_0_1(client, library, monkeypatch):
    monkeypatch.setattr(feed_auth, "_client_host", lambda request: "192.168.178.50")
    r = client.get(f"{P}/feed/next", headers=_h())
    assert r.status_code == 403


@pytest.mark.parametrize("fwd", ["192.168.178.50", "127.0.0.1"])
def test_weitergeleitete_anfrage_gilt_als_aussen(client, library, fwd):
    """Kommt die Anfrage über nginx (X-Forwarded-For / X-Real-IP), ist sie nicht lokal – auch mit Schlüssel nicht."""
    for hdr in ("X-Forwarded-For", "X-Real-IP"):
        r = client.get(f"{P}/feed/next", headers={**_h(), hdr: fwd})
        assert r.status_code == 403


def test_benutzeranmeldung_oeffnet_den_feed_nicht(client, library, admin_headers):
    assert client.get(f"{P}/feed/next", headers=admin_headers).status_code == 403


def test_datei_wird_gestreamt(client, library):
    url = client.get(f"{P}/feed/next", headers=_h()).text.strip().split(":", 1)[1].split('"')[-1].lstrip(":")
    path = url[url.index(P):]
    r = client.get(path, headers=_h())
    assert r.status_code == 200 and len(r.content) > 1000
    assert r.headers["content-type"] in ("audio/mpeg", "audio/flac", "application/octet-stream")


def test_unbekannter_titel_404(client, library):
    assert client.get(f"{P}/feed/file/gibt-es-nicht", headers=_h()).status_code == 404


def test_leere_bibliothek_klare_meldung(client, admin_headers, safe, fake_share, feed_key):
    _configure(client, admin_headers, safe)
    r = client.get(f"{P}/feed/next", headers=_h())
    assert r.status_code == 503 and r.json()["detail"]["code"] == "radiostream_library_empty"


def test_schluessel_nie_im_log(client, library, caplog):
    caplog.set_level(logging.DEBUG)
    client.get(f"{P}/feed/next", headers=_h())
    client.get(f"{P}/feed/next", headers=_h("falsch"))
    assert KEY not in caplog.text


def test_vergleich_zeitkonstant():
    import inspect
    assert "compare_digest" in inspect.getsource(feed_auth)


def test_leerer_schluessel_in_der_datei_sperrt_alles(client, library, monkeypatch, tmp_path):
    """Leerer Wert in der Datei + leerer Kopf darf NICHT als „gleich“ durchgehen."""
    f = tmp_path / "leer.env"
    f.write_text("RADIOSTREAM_FEED_KEY=\n")
    monkeypatch.setattr(feed_auth, "SECRETS_FILE", f)
    for hdr in ({}, {"X-Radiostream-Feed": ""}):
        assert client.get(f"{P}/feed/next", headers=hdr).status_code == 403


def test_nur_der_genaue_name_zaehlt(monkeypatch, tmp_path):
    f = tmp_path / "s.env"
    f.write_text("OLD_RADIOSTREAM_FEED_KEY=falsch\nRADIOSTREAM_FEED_KEY_BACKUP=auch-falsch\nRADIOSTREAM_FEED_KEY=richtig\n")
    monkeypatch.setattr(feed_auth, "SECRETS_FILE", f)
    assert feed_auth.read_secret("RADIOSTREAM_FEED_KEY") == "richtig"


def test_titel_mit_anfuehrungszeichen_bricht_die_anweisung_nicht(client, library):
    """Ein Titel mit " oder Zeilenumbruch darf die Liquidsoap-Anweisung nicht beenden oder umlenken."""
    from hydrahive.db.connection import db
    with db() as conn:
        conn.execute("""UPDATE module_radiostream_tracks SET title = 'Böse",title="x":http://8.8.8.8/x
neu', artist = 'A\\"B'""")
        conn.commit()
    body = client.get(f"{P}/feed/next", headers=_h()).text
    assert body.count('"') == 4                                  # genau artist="…" und title="…"
    assert body.count("\n") == 1 and body.endswith("\n")         # eine Zeile, kein eingeschleuster Umbruch
    meta, url = body.rstrip("\n").rsplit('":', 1)
    assert url.startswith("http://127.0.0.1:") and "/feed/file/" in url
