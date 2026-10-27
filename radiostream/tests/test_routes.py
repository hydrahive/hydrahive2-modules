"""Schnittstellen Etappe 1 (SPEC „Schnittstellen“): Einstellungen, Einlesen, Suche, Statistik, Vorhören, Rechte.

Das Passwort aus dem Safe darf nie in einer Antwort, der DB oder dem Log stehen.
"""
from __future__ import annotations

import logging

import pytest
from backend import scanner, settings_store
from conftest import MOD_PREFIX, SECRET
from smb_fake import audio

P = MOD_PREFIX


def _configure(client, admin_headers, safe, url="smb://nas.test/Musik"):
    r = client.put(f"{P}/settings", headers=admin_headers, json={"url": url, "credential_name": safe})
    assert r.status_code == 200, r.text
    return r.json()


def _fill(fake_share):
    fake_share.put("ABBA/Arrival/01 Dancing Queen.mp3",
                   audio("mp3", artist="ABBA", title="Dancing Queen", album="Arrival", genre="Pop", date="1976"))
    fake_share.put("Die Ärzte/Die Bestie in Menschengestalt/02 Schrei nach Liebe.mp3",
                   audio("mp3", artist="Die Ärzte", title="Schrei nach Liebe", genre="Punk", date="1993"))
    fake_share.put("Queen/Innuendo/06 The Show Must Go On.flac",
                   audio("flac", artist="Queen", title="The Show Must Go On", genre="Rock", date="1991"))
    fake_share.put("Queen/A Kind of Magic/01 One Vision.mp3",
                   audio("mp3", artist="Queen", title="One Vision", genre="Rock", date="1986"))


@pytest.fixture
def filled(client, admin_headers, safe, fake_share):
    _configure(client, admin_headers, safe)
    _fill(fake_share)
    scanner.run_scan()
    return fake_share


# --- Einstellungen ----------------------------------------------------------------------------------------------

def test_einstellungen_speichern_ohne_passwort(client, admin_headers, safe, caplog):
    caplog.set_level(logging.DEBUG)
    body = _configure(client, admin_headers, safe)
    assert body["url"] == "smb://nas.test/Musik" and body["credential_name"] == "plexmusik"
    assert SECRET not in str(body)
    got = client.get(f"{P}/settings", headers=admin_headers).json()
    assert got["url"] == "smb://nas.test/Musik" and SECRET not in str(got)
    from hydrahive.db.connection import db
    with db() as conn:
        rows = conn.execute("SELECT * FROM module_radiostream_sources").fetchall()
    assert rows and SECRET not in str([tuple(r) for r in rows])
    assert SECRET not in caplog.text


def test_einstellungen_ohne_quelle(client, admin_headers):
    r = client.get(f"{P}/settings", headers=admin_headers)
    assert r.status_code == 200 and r.json()["url"] is None


@pytest.mark.parametrize("url", ["http://nas/Musik", "smb://", "smb://nas", "smb://na s/x", "smb://nas/../x",
                                 "smb://nas/Musik/../../etc", "file:///etc"])
def test_einstellungen_falsche_adresse(client, admin_headers, safe, url):
    r = client.put(f"{P}/settings", headers=admin_headers, json={"url": url, "credential_name": safe})
    assert r.status_code == 400 and r.json()["detail"]["code"] == "radiostream_url_invalid"


def test_einstellungen_unbekannter_safe_eintrag(client, admin_headers):
    r = client.put(f"{P}/settings", headers=admin_headers, json={"url": "smb://nas.test/Musik",
                                                                 "credential_name": "gibtsnicht"})
    assert r.status_code == 400 and r.json()["detail"]["code"] == "radiostream_credential_invalid"


def test_einstellungen_safe_eintrag_falscher_typ(client, admin_headers):
    from hydrahive.credentials.models import Credential
    from hydrahive.credentials.store import delete_credential, save_credential
    save_credential("boss", Credential(name="tok", type="bearer", value="x", url_pattern="https://x.test/*"))
    try:
        r = client.put(f"{P}/settings", headers=admin_headers, json={"url": "smb://nas.test/Musik",
                                                                     "credential_name": "tok"})
        assert r.status_code == 400 and r.json()["detail"]["code"] == "radiostream_credential_invalid"
    finally:
        delete_credential("boss", "tok")


def test_safe_eintraege_zur_auswahl(client, admin_headers, safe):
    r = client.get(f"{P}/credentials", headers=admin_headers)
    assert r.status_code == 200
    items = r.json()["items"]
    assert {"name": "plexmusik", "url_pattern": "smb://nas.test/Musik/"} in items
    assert SECRET not in str(r.json())


def test_verbindung_pruefen(client, admin_headers, safe, fake_share):
    _fill(fake_share)
    r = client.post(f"{P}/settings/test", headers=admin_headers,
                    json={"url": "smb://nas.test/Musik", "credential_name": safe})
    assert r.status_code == 200 and r.json() == {"ok": True, "top_dirs": 3}


@pytest.mark.parametrize("fail,code", [("unreachable", "radiostream_source_unreachable"),
                                       ("auth", "radiostream_auth_failed"),
                                       ("share", "radiostream_share_not_found")])
def test_verbindung_pruefen_fehler(client, admin_headers, safe, fake_share, fail, code):
    fake_share.fail = fail
    r = client.post(f"{P}/settings/test", headers=admin_headers,
                    json={"url": "smb://nas.test/Musik", "credential_name": safe})
    assert r.status_code == 502 and r.json()["detail"]["code"] == code
    assert SECRET not in r.text


# --- Rechte -----------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("method,path", [("put", "/settings"), ("post", "/settings/test"), ("post", "/scan"),
                                         ("post", "/scan/cancel"), ("get", "/credentials"), ("get", "/settings")])
def test_einstellungen_und_einlesen_nur_admin(client, user_headers, method, path):
    kw = {"json": {}} if method != "get" else {}
    r = getattr(client, method)(f"{P}{path}", headers=user_headers, **kw)
    assert r.status_code == 403 and r.json()["detail"]["code"] == "radiostream_admin_only"


@pytest.mark.parametrize("path", ["/tracks", "/stats", "/scan", "/artists", "/genres"])
def test_ohne_anmeldung_401(client, path):
    assert client.get(f"{P}{path}").status_code == 401


def test_nutzer_darf_suchen(client, user_headers, filled):
    r = client.get(f"{P}/tracks", headers=user_headers)
    assert r.status_code == 200 and len(r.json()["items"]) == 4


# --- Einlesen über die Schnittstelle --------------------------------------------------------------------------------

def test_einlesen_starten_und_stand(client, admin_headers, safe, fake_share, monkeypatch):
    _configure(client, admin_headers, safe)
    _fill(fake_share)
    started = {}
    monkeypatch.setattr(scanner, "start_in_background", lambda: started.setdefault("ok", True))
    r = client.post(f"{P}/scan", headers=admin_headers)
    assert r.status_code == 202 and started == {"ok": True}
    st = client.get(f"{P}/scan", headers=admin_headers).json()
    assert {"running", "dirs_seen", "files_seen", "added", "updated", "missing", "errors", "eta_s"} <= set(st)


def test_einlesen_ohne_quelle(client, admin_headers):
    r = client.post(f"{P}/scan", headers=admin_headers)
    assert r.status_code == 409 and r.json()["detail"]["code"] == "radiostream_not_configured"


def test_einlesen_laeuft_schon(client, admin_headers, safe):
    _configure(client, admin_headers, safe)
    from backend import scan_state
    assert scan_state.try_begin()
    try:
        r = client.post(f"{P}/scan", headers=admin_headers)
        assert r.status_code == 409 and r.json()["detail"]["code"] == "radiostream_scan_running"
    finally:
        scan_state.finish()


def test_einlesen_im_hintergrund_echt(client, admin_headers, safe, fake_share):
    """start_in_background startet wirklich einen Thread und endet mit Ergebnis (ohne Ereignisschleife zu blockieren)."""
    import time
    _configure(client, admin_headers, safe)
    _fill(fake_share)
    r = client.post(f"{P}/scan", headers=admin_headers)
    assert r.status_code == 202
    for _ in range(100):
        st = client.get(f"{P}/scan", headers=admin_headers).json()
        if not st["running"] and st["finished_at"]:
            break
        time.sleep(0.05)
    assert st["added"] == 4 and st["running"] is False


# --- Suche ------------------------------------------------------------------------------------------------------

def test_volltextsuche_ohne_umlaute(client, user_headers, filled):
    items = client.get(f"{P}/tracks", headers=user_headers, params={"q": "arzte liebe"}).json()["items"]
    assert [i["title"] for i in items] == ["Schrei nach Liebe"]


def test_suche_teilwort(client, user_headers, filled):
    items = client.get(f"{P}/tracks", headers=user_headers, params={"q": "danc"}).json()["items"]
    assert [i["title"] for i in items] == ["Dancing Queen"]


def test_suche_sonderzeichen_kein_fehler(client, user_headers, filled):
    for q in ('"', "AND", "a*b(", "NOT OR", "-", "'; DROP TABLE"):
        r = client.get(f"{P}/tracks", headers=user_headers, params={"q": q})
        assert r.status_code == 200, q


def test_filter_genre_jahrzehnt_format(client, user_headers, filled):
    g = client.get(f"{P}/tracks", headers=user_headers, params={"genre": "Rock"}).json()["items"]
    assert {i["title"] for i in g} == {"The Show Must Go On", "One Vision"}
    y = client.get(f"{P}/tracks", headers=user_headers, params={"year_from": 1990, "year_to": 1999}).json()["items"]
    assert {i["title"] for i in y} == {"The Show Must Go On", "Schrei nach Liebe"}
    f = client.get(f"{P}/tracks", headers=user_headers, params={"format": "flac"}).json()["items"]
    assert [i["title"] for i in f] == ["The Show Must Go On"]


def test_sortierung_kuenstler_album_titel(client, user_headers, filled):
    items = client.get(f"{P}/tracks", headers=user_headers).json()["items"]
    assert [i["artist"] for i in items] == ["ABBA", "Die Ärzte", "Queen", "Queen"]


def test_blaettern_mit_cursor(client, user_headers, filled):
    a = client.get(f"{P}/tracks", headers=user_headers, params={"limit": 3}).json()
    assert len(a["items"]) == 3 and a["next_cursor"]
    b = client.get(f"{P}/tracks", headers=user_headers, params={"limit": 3, "cursor": a["next_cursor"]}).json()
    assert len(b["items"]) == 1 and b["next_cursor"] is None
    ids = [i["track_id"] for i in a["items"] + b["items"]]
    assert len(set(ids)) == 4


def test_limit_hoechstens_200(client, user_headers, filled):
    r = client.get(f"{P}/tracks", headers=user_headers, params={"limit": 5000})
    assert r.status_code == 422


def test_fehlende_titel_standardmaessig_ausgeblendet(client, user_headers, filled):
    filled.remove("ABBA/Arrival/01 Dancing Queen.mp3")
    scanner.run_scan()
    items = client.get(f"{P}/tracks", headers=user_headers).json()["items"]
    assert "Dancing Queen" not in [i["title"] for i in items]
    miss = client.get(f"{P}/tracks", headers=user_headers, params={"state": "missing"}).json()["items"]
    assert [i["title"] for i in miss] == ["Dancing Queen"]


def test_antwort_ohne_interne_felder(client, user_headers, filled):
    item = client.get(f"{P}/tracks", headers=user_headers).json()["items"][0]
    assert {"track_id", "artist", "title", "album", "genre", "year", "duration_s", "format"} <= set(item)
    assert "rowid" not in item and "source_id" not in item


# --- Statistik, Künstler, Genres ---------------------------------------------------------------------------------

def test_statistik(client, user_headers, filled):
    s = client.get(f"{P}/stats", headers=user_headers).json()
    assert s["tracks"] == 4 and s["artists"] == 3 and s["missing"] == 0 and s["errors"] == 0
    assert 6 < s["duration_s"] < 10
    assert s["formats"] == {"mp3": 3, "flac": 1}
    assert s["genres"][0] == {"genre": "Rock", "count": 2}
    assert {"decade": 1990, "count": 2} in s["decades"]


def test_kuenstler_und_genres(client, user_headers, filled):
    a = client.get(f"{P}/artists", headers=user_headers).json()["items"]
    assert {"artist": "Queen", "count": 2} in a
    g = client.get(f"{P}/genres", headers=user_headers).json()["items"]
    assert g[0] == {"genre": "Rock", "count": 2}


# --- Vorhören ---------------------------------------------------------------------------------------------------

def _id(client, headers, title):
    items = client.get(f"{P}/tracks", headers=headers, params={"q": title}).json()["items"]
    return items[0]["track_id"]


def test_vorhoeren_mp3_direkt_mit_range(client, user_headers, filled):
    tid = _id(client, user_headers, "Dancing Queen")
    r = client.get(f"{P}/tracks/{tid}/audio", headers=user_headers)
    assert r.status_code == 200 and r.headers["content-type"] == "audio/mpeg"
    assert r.headers.get("accept-ranges") == "bytes"
    full = r.content
    r2 = client.get(f"{P}/tracks/{tid}/audio", headers={**user_headers, "Range": "bytes=10-19"})
    assert r2.status_code == 206 and r2.content == full[10:20]
    assert r2.headers["content-range"] == f"bytes 10-19/{len(full)}"


def test_vorhoeren_flac_wird_umgewandelt(client, user_headers, filled, monkeypatch):
    from backend import audio as audio_mod
    seen = {}

    def fake_transcode(src, fmt):
        seen["fmt"] = fmt
        seen["head"] = src.read(4)
        yield b"ID3-umgewandelt"

    monkeypatch.setattr(audio_mod, "transcode_mp3", fake_transcode)
    tid = _id(client, user_headers, "Show Must")
    r = client.get(f"{P}/tracks/{tid}/audio", headers=user_headers)
    assert r.status_code == 200 and r.headers["content-type"] == "audio/mpeg"
    assert r.content == b"ID3-umgewandelt" and seen == {"fmt": "flac", "head": b"fLaC"}


def test_vorhoeren_unbekannter_titel(client, user_headers, filled):
    r = client.get(f"{P}/tracks/t_gibtsnicht/audio", headers=user_headers)
    assert r.status_code == 404 and r.json()["detail"]["code"] == "radiostream_track_not_found"


def test_vorhoeren_datei_weg(client, user_headers, filled):
    tid = _id(client, user_headers, "Dancing Queen")
    filled.broken_open.add("ABBA/Arrival/01 Dancing Queen.mp3")
    r = client.get(f"{P}/tracks/{tid}/audio", headers=user_headers)
    assert r.status_code == 502 and r.json()["detail"]["code"] == "radiostream_track_unavailable"


def test_vorhoeren_ohne_anmeldung(client, filled, admin_headers):
    tid = _id(client, admin_headers, "Dancing Queen")
    assert client.get(f"{P}/tracks/{tid}/audio").status_code == 401


def test_quelle_wechseln_loescht_nichts(client, admin_headers, filled, safe):
    """Eine andere Adresse eintragen: alte Titel bleiben (Quelle wird ersetzt, Titel gehören weiter zur Bibliothek)."""
    _configure(client, admin_headers, safe, url="smb://nas.test/Musik2")
    s = client.get(f"{P}/stats", headers=admin_headers).json()
    assert s["tracks"] == 4
    assert settings_store.get()["url"] == "smb://nas.test/Musik2"



# --- Nachschärfung nach Mutanten (27.10.) ------------------------------------------------------------------------

def test_jahresgrenzen_inklusive(client, user_headers, filled):
    y = client.get(f"{P}/tracks", headers=user_headers, params={"year_from": 1986, "year_to": 1991}).json()["items"]
    assert {i["title"] for i in y} == {"One Vision", "The Show Must Go On"}


def test_cursor_bei_genau_voller_seite(client, user_headers, filled):
    a = client.get(f"{P}/tracks", headers=user_headers, params={"limit": 4}).json()
    assert len(a["items"]) == 4 and a["next_cursor"] is None


def test_genre_filter_ohne_gross_klein(client, user_headers, filled):
    g = client.get(f"{P}/tracks", headers=user_headers, params={"genre": "rock"}).json()["items"]
    assert {i["title"] for i in g} == {"The Show Must Go On", "One Vision"}


def test_safe_auswahl_nur_benutzer_passwort(client, admin_headers, safe):
    from hydrahive.credentials.models import Credential
    from hydrahive.credentials.store import delete_credential, save_credential
    save_credential("boss", Credential(name="tok", type="bearer", value="x", url_pattern="https://x.test/*"))
    try:
        names = [i["name"] for i in client.get(f"{P}/credentials", headers=admin_headers).json()["items"]]
        assert "plexmusik" in names and "tok" not in names
    finally:
        delete_credential("boss", "tok")


def test_range_ausserhalb_der_datei(client, user_headers, filled):
    tid = _id(client, user_headers, "Dancing Queen")
    size = len(client.get(f"{P}/tracks/{tid}/audio", headers=user_headers).content)
    r = client.get(f"{P}/tracks/{tid}/audio", headers={**user_headers, "Range": f"bytes={size + 10}-"})
    assert r.status_code == 200 and len(r.content) == size       # ungültiger Bereich → ganze Datei
