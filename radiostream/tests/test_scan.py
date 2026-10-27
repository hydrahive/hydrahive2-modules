"""Einlesen der Bibliothek (SPEC „Bauplan Etappe 1 – Einlesen“).

Gegen die SMB-Attrappe: neu, unverändert, geändert, verschwunden, wieder da, kaputt, Tags aus dem Pfad,
Fortsetzen nach Abbruch, ein Strang, nur lesen. Nie ein echtes SMB.
"""
from __future__ import annotations

import pytest
from smb_fake import audio

from backend import library, scanner, settings_store


@pytest.fixture
def source(db_ready, safe, fake_share):
    settings_store.save(owner="boss", url="smb://nas.test/Musik", credential_name=safe)
    return settings_store.get()


def _scan(**kw):
    return scanner.run_scan(**kw)


def _track(rel):
    return library.by_path(rel)


def test_neue_titel_mit_tags(source, fake_share):
    fake_share.put("ABBA/Arrival/01 Dancing Queen.mp3",
                   audio("mp3", artist="ABBA", title="Dancing Queen", album="Arrival", genre="Pop",
                         date="1976", tracknumber="1/10"))
    fake_share.put("Queen/Innuendo/06 The Show Must Go On.flac",
                   audio("flac", artist="Queen", title="The Show Must Go On", album="Innuendo", genre="Rock",
                         date="1991-02-04", albumartist="Queen"))
    r = _scan()
    assert r.added == 2 and r.updated == 0 and r.missing == 0 and r.errors == 0
    t = _track("ABBA/Arrival/01 Dancing Queen.mp3")
    assert (t["artist"], t["title"], t["album"], t["genre"], t["year"], t["track_no"]) == \
        ("ABBA", "Dancing Queen", "Arrival", "Pop", 1976, 1)
    assert t["format"] == "mp3" and t["state"] == "ok"
    assert 1.5 < t["duration_s"] < 2.5 and t["sample_rate"] == 22050 and t["bitrate"] > 0
    f = _track("Queen/Innuendo/06 The Show Must Go On.flac")
    assert f["format"] == "flac" and f["year"] == 1991 and f["album_artist"] == "Queen"


def test_ohne_tags_aus_dem_pfad(source, fake_share):
    fake_share.put("Nena/99 Luftballons/03 - Leuchtturm.mp3", audio("mp3"))
    fake_share.put("Einzeln/Track.flac", audio("flac"))
    _scan()
    t = _track("Nena/99 Luftballons/03 - Leuchtturm.mp3")
    assert (t["artist"], t["album"], t["title"], t["track_no"]) == ("Nena", "99 Luftballons", "Leuchtturm", 3)
    e = _track("Einzeln/Track.flac")
    assert (e["artist"], e["album"], e["title"]) == ("Einzeln", "", "Track")


def test_nur_audio_dateien(source, fake_share):
    fake_share.put("A/B/cover.jpg", b"\xff\xd8")
    fake_share.put("A/B/info.nfo", b"x")
    fake_share.put("A/B/liste.m3u", b"x")
    fake_share.put("A/B/01 Lied.MP3", audio("mp3"))
    r = _scan()
    assert r.added == 1
    assert library.count() == 1


def test_unveraenderte_werden_nicht_geoeffnet(source, fake_share):
    fake_share.put("A/B/01 x.mp3", audio("mp3", title="x"))
    _scan()
    fake_share.opened.clear()
    r = _scan()
    assert r.added == 0 and r.updated == 0 and r.unchanged == 1
    assert fake_share.opened == []


def test_geaenderte_werden_neu_gelesen(source, fake_share):
    fake_share.put("A/B/01 x.mp3", audio("mp3", title="alt"), mtime=1)
    _scan()
    tid = _track("A/B/01 x.mp3")["track_id"]
    fake_share.put("A/B/01 x.mp3", audio("mp3", title="neu"), mtime=2)
    r = _scan()
    assert r.updated == 1
    t = _track("A/B/01 x.mp3")
    assert t["title"] == "neu" and t["track_id"] == tid          # gleiche ID bleibt (später Historie)


def test_verschwunden_wird_markiert_nicht_geloescht_und_kommt_zurueck(source, fake_share):
    fake_share.put("A/B/01 x.mp3", audio("mp3", title="x"))
    _scan()
    fake_share.remove("A/B/01 x.mp3")
    r = _scan()
    assert r.missing == 1
    assert _track("A/B/01 x.mp3")["state"] == "missing"
    fake_share.put("A/B/01 x.mp3", audio("mp3", title="x"))
    _scan()
    assert _track("A/B/01 x.mp3")["state"] == "ok"


def test_kaputte_datei_bricht_nichts_ab(source, fake_share):
    fake_share.put("A/B/01 kaputt.mp3", b"keine musik")
    fake_share.put("A/B/02 nicht lesbar.flac", audio("flac"))
    fake_share.broken_open.add("A/B/02 nicht lesbar.flac")
    fake_share.put("A/B/03 gut.mp3", audio("mp3", title="gut"))
    r = _scan()
    assert r.added == 1 and r.errors == 2
    assert _track("A/B/03 gut.mp3")["title"] == "gut"
    errs = {e["rel_path"]: e["code"] for e in library.scan_errors()}
    assert errs == {"A/B/01 kaputt.mp3": "unreadable_tags", "A/B/02 nicht lesbar.flac": "read_failed"}


def test_kaputte_datei_spaeter_repariert(source, fake_share):
    fake_share.put("A/B/01 x.mp3", b"keine musik", mtime=1)
    _scan()
    assert _track("A/B/01 x.mp3") is None
    fake_share.put("A/B/01 x.mp3", audio("mp3", title="jetzt gut"), mtime=2)
    r = _scan()
    assert r.added == 1 and _track("A/B/01 x.mp3")["title"] == "jetzt gut"


def test_fortsetzen_nach_abbruch(source, fake_share, monkeypatch):
    for i in range(12):
        fake_share.put(f"K/A/{i:02d} t.mp3", audio("mp3", title=f"t{i}"))
    monkeypatch.setattr(scanner, "BATCH", 5)
    calls = {"n": 0}
    orig = scanner._read_tags

    def boom(conn, rel):
        calls["n"] += 1
        if calls["n"] == 8:
            raise KeyboardInterrupt  # harter Abbruch mitten im zweiten Paket
        return orig(conn, rel)

    monkeypatch.setattr(scanner, "_read_tags", boom)
    with pytest.raises(KeyboardInterrupt):
        _scan()
    assert library.count() == 5                     # erstes Paket ist gespeichert
    monkeypatch.setattr(scanner, "_read_tags", orig)
    fake_share.opened.clear()
    r = _scan()
    assert library.count() == 12 and r.added == 7
    assert len(fake_share.opened) == 7              # die schon gespeicherten 5 werden nicht neu gelesen


def test_abbrechen_auf_wunsch(source, fake_share, monkeypatch):
    for i in range(6):
        fake_share.put(f"K/A/{i:02d} t.mp3", audio("mp3"))
    from backend import scan_state
    monkeypatch.setattr(scanner, "BATCH", 2)
    orig = scanner._read_tags

    def stop_after_three(conn, rel):
        if len(fake_share.opened) == 3:
            scan_state.request_cancel()
        return orig(conn, rel)

    monkeypatch.setattr(scanner, "_read_tags", stop_after_three)
    r = _scan()
    assert r.cancelled is True
    assert library.count() < 6
    # Abbrechen markiert nichts als verschwunden (Durchgang war unvollständig)
    assert all(t["state"] == "ok" for t in library.all_tracks())


def test_unvollstaendiger_durchgang_markiert_nichts_als_fehlend(source, fake_share, monkeypatch):
    fake_share.put("A/B/01 x.mp3", audio("mp3"))
    _scan()
    fake_share.remove("A/B/01 x.mp3")
    from backend import scan_state
    monkeypatch.setattr(scan_state, "cancelled", lambda: True)   # Abbruch während des Durchgangs
    r = _scan()
    assert r.cancelled is True and r.missing == 0
    assert _track("A/B/01 x.mp3")["state"] == "ok"


def test_abbrechen_ohne_laufenden_durchgang_stoppt_den_naechsten_nicht(source, fake_share):
    from backend import scan_state
    fake_share.put("A/B/01 x.mp3", audio("mp3"))
    scan_state.request_cancel()
    r = _scan()
    assert r.cancelled is False and r.added == 1


def test_ein_strang_und_nur_lesen(source, fake_share):
    assert scanner.WORKERS == 1                     # Till 26.10.: „gemütlich reicht“
    fake_share.put("A/B/01 x.mp3", audio("mp3"))
    _scan()
    import inspect
    src = inspect.getsource(scanner) + inspect.getsource(__import__("backend.smb_source", fromlist=["x"]))
    for bad in ("mode=\"w", "mode='w", "\"wb\"", "'wb'", ".save(", "remove(", "rename(", "makedirs(", "mkdir("):
        assert bad not in src, bad


def test_anmeldung_mit_safe_zugang(source, fake_share):
    from conftest import SECRET
    fake_share.put("A/B/01 x.mp3", audio("mp3"))
    _scan()
    assert fake_share.logins[-1] == ("nas.test", "Musik", "musik", SECRET)


def test_unterordner_als_quelle(db_ready, safe, fake_share):
    settings_store.save(owner="boss", url="smb://nas.test/Musik/Rock", credential_name=safe)
    fake_share.put("Rock/AC-DC/Back in Black/01 Hells Bells.mp3", audio("mp3", title="Hells Bells"))
    fake_share.put("Pop/ABBA/x/01 y.mp3", audio("mp3"))
    _scan()
    assert library.count() == 1
    assert _track("AC-DC/Back in Black/01 Hells Bells.mp3")["title"] == "Hells Bells"


def test_ohne_quelle_fehler(db_ready, fake_share):
    from backend.smb_source import SourceError
    with pytest.raises(SourceError) as e:
        _scan()
    assert e.value.code == "radiostream_not_configured"


@pytest.mark.parametrize("fail,code", [("unreachable", "radiostream_source_unreachable"),
                                       ("auth", "radiostream_auth_failed"),
                                       ("share", "radiostream_share_not_found")])
def test_verbindungsfehler_wird_gemerkt(source, fake_share, fail, code):
    from backend.smb_source import SourceError
    fake_share.fail = fail
    with pytest.raises(SourceError):
        _scan()
    s = settings_store.get()
    assert s["state"] == "error" and s["last_scan_error"] == code


def test_fortschritt_wird_gemeldet(source, fake_share):
    from backend import scan_state
    for i in range(3):
        fake_share.put(f"K/A/{i:02d} t.mp3", audio("mp3"))
    _scan()
    st = scan_state.snapshot()
    assert st["running"] is False
    assert st["dirs_seen"] == 1 and st["files_seen"] == 3 and st["added"] == 3
    assert st["finished_at"] and st["started_at"]
