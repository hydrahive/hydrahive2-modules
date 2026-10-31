"""Auswahl des nächsten Titels (PLAN-PROGRAMM.md „Auswahl“): Warteschlange → Playlist/Mix → Alles (mit Ausschluss).
Nie Stille: leere Playlist/Mix → Alles + Hinweis."""
from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta

import pytest
from backend import choose, program, rotation

T0 = datetime(2026, 10, 31, 12, 0, tzinfo=UTC)


def _track(tid, artist=None, genre="Pop", state="ok", dur=200, rel=None):
    from hydrahive.db.connection import db
    with db() as conn:
        conn.execute("INSERT INTO module_radiostream_tracks (track_id, source_id, rel_path, size, mtime, artist, title, "
                     "genre, format, duration_s, state, first_seen, last_seen) VALUES (?, 'main', ?, 1, 1, ?, ?, ?, "
                     "'mp3', ?, ?, 'x', 'x')", (tid, rel or f"{artist or tid}/{tid}.mp3", artist or f"K-{tid}",
                                                f"T {tid}", genre, dur, state))
        conn.commit()


def nxt(i=0, now=T0):
    return choose.next_track(now=now, rng=random.Random(i))


def test_alles_ohne_hoerbuecher_und_ohne_lange(db_ready):
    _track("m1")
    _track("bibi", genre="Kids; Audiobooks")
    _track("lang", dur=2000)
    got = {nxt(i)["track_id"] for i in range(40)}
    assert got == {"m1"}


def test_alles_mit_eigenem_ausschluss_und_langen(db_ready):
    _track("m1", genre="Rock")
    _track("c1", genre="Comedy")
    _track("lang", genre="Rock", dur=2000)
    program.save_exclude({"genres": ["Comedy"], "genre_parts": [], "folders": []}, allow_long=True, user="boss")
    got = {nxt(i)["track_id"] for i in range(60)}
    assert got == {"m1", "lang"}


def test_warteschlange_zuerst_und_wird_verbraucht(db_ready):
    for t in ("a", "b", "c"):
        _track(t)
    program.enqueue("b", user="boss")
    program.enqueue("c", user="boss")
    assert nxt()["track_id"] == "b" and nxt()["track_id"] == "c"
    assert program.queue() == []
    assert nxt()["source"] == "all"


def test_warteschlange_ignoriert_sperren(db_ready):
    _track("a", artist="Queen")
    rotation.record("a", "Queen", at=T0 - timedelta(minutes=1))
    program.enqueue("a", user="boss")
    got = nxt()
    assert got["track_id"] == "a" and got["source"] == "queue"


def test_warteschlange_titel_inzwischen_weg(db_ready):
    _track("a")
    _track("b", state="ok")
    program.enqueue("b", user="boss")
    from hydrahive.db.connection import db
    with db() as conn:
        conn.execute("UPDATE module_radiostream_tracks SET state = 'missing' WHERE track_id = 'b'")
        conn.commit()
    assert nxt()["track_id"] == "a"


def test_playlist_der_reihe_nach_und_von_vorn(db_ready):
    for t in ("p1", "p2", "p3"):
        _track(t, artist="Gleich")                          # Sperren gelten bei Playlisten nicht
    pl = program.create_playlist("A", user="boss")
    program.add_items(pl["id"], ["p1", "p2", "p3"])
    program.set_program("playlist", pl["id"], user="boss")
    assert [nxt()["track_id"] for _ in range(5)] == ["p1", "p2", "p3", "p1", "p2"]
    assert nxt()["source"] == "playlist"


def test_playlist_am_ende_zurueck_zu_alles(db_ready):
    _track("p1")
    _track("x")
    pl = program.create_playlist("A", user="boss")
    program.add_items(pl["id"], ["p1"])
    program.update_playlist(pl["id"], at_end="back")
    program.set_program("playlist", pl["id"], user="boss")
    assert nxt()["track_id"] == "p1"
    got = nxt()
    assert got["source"] == "all" and program.get_program()["mode"] == "all"


def test_playlist_gemischt_jeder_einmal_dann_neue_runde(db_ready):
    ids = [f"s{i}" for i in range(6)]
    for t in ids:
        _track(t)
    pl = program.create_playlist("A", user="boss")
    program.add_items(pl["id"], ids)
    program.update_playlist(pl["id"], order_mode="shuffle")
    program.set_program("playlist", pl["id"], user="boss")
    first = [nxt(i)["track_id"] for i in range(6)]
    assert sorted(first) == sorted(ids) and first != ids
    second = [nxt(10 + i)["track_id"] for i in range(6)]
    assert sorted(second) == sorted(ids)


def test_playlist_ueberspringt_fehlende(db_ready):
    _track("p1")
    _track("p2", state="missing")
    _track("p3")
    pl = program.create_playlist("A", user="boss")
    program.add_items(pl["id"], ["p1", "p2", "p3"])
    program.set_program("playlist", pl["id"], user="boss")
    assert [nxt()["track_id"] for _ in range(3)] == ["p1", "p3", "p1"]


def test_leere_playlist_fallback_alles_mit_hinweis(db_ready):
    _track("x")
    pl = program.create_playlist("Leer", user="boss")
    program.set_program("playlist", pl["id"], user="boss")
    got = nxt()
    assert got["track_id"] == "x" and got["source"] == "all"
    assert program.get_program()["notice"] == "radiostream_program_empty"
    assert program.get_program()["mode"] == "playlist"                 # Wahl bleibt, Hinweis zeigt das Problem


def test_mix_mit_sperren(db_ready):
    _track("r1", artist="Queen", genre="Rock")
    _track("r2", artist="Queen", genre="Rock")
    _track("r3", artist="AC/DC", genre="Hard Rock;Rock")
    _track("p1", genre="Pop")
    m = program.save_mix(None, name="Rock", rules_={"genres": ["Rock"]}, allow_long=False, user="boss")
    program.set_program("mix", m["id"], user="boss")
    rotation.record("r1", "Queen", at=T0 - timedelta(minutes=5))
    got = {nxt(i)["track_id"] for i in range(30)}
    assert got == {"r3"}


def test_mix_ohne_ausschluss_von_alles(db_ready):
    """Ein Mix gilt genau so, wie er gebaut ist – „Ausgeschlossen von Alles“ betrifft nur „Alles“."""
    _track("h1", genre="Hörspiel", artist="Hui Buh")
    m = program.save_mix(None, name="Hörspiele", rules_={"genres": ["Hörspiel"]}, allow_long=False, user="boss")
    program.set_program("mix", m["id"], user="boss")
    assert nxt()["track_id"] == "h1"


def test_mix_zu_klein_lockert_sperren_nie_stille(db_ready):
    _track("r1", artist="Queen", genre="Rock")
    m = program.save_mix(None, name="Rock", rules_={"genres": ["Rock"]}, allow_long=False, user="boss")
    program.set_program("mix", m["id"], user="boss")
    rotation.record("r1", "Queen", at=T0 - timedelta(minutes=1))
    got = nxt()
    assert got["track_id"] == "r1" and got["relaxed"] is True


def test_leerer_mix_fallback_alles(db_ready):
    _track("x", genre="Pop")
    m = program.save_mix(None, name="Jazz", rules_={"genres": ["Jazz"]}, allow_long=False, user="boss")
    program.set_program("mix", m["id"], user="boss")
    got = nxt()
    assert got["track_id"] == "x" and got["source"] == "all"
    assert program.get_program()["notice"] == "radiostream_program_empty"


def test_hinweis_verschwindet_wenn_wieder_titel_da(db_ready):
    m = program.save_mix(None, name="Jazz", rules_={"genres": ["Jazz"]}, allow_long=False, user="boss")
    program.set_program("mix", m["id"], user="boss")
    _track("x", genre="Pop")
    nxt()
    _track("j", genre="Jazz")
    assert nxt()["track_id"] == "j" and program.get_program()["notice"] == ""


def test_alles_ausgeschlossen_lieber_ausschluss_ignorieren_als_stille(db_ready):
    _track("bibi", genre="Kids; Audiobooks")
    got = nxt()
    assert got["track_id"] == "bibi" and got["relaxed"] is True


def test_leere_bibliothek(db_ready):
    with pytest.raises(rotation.NothingToPlay):
        nxt()


def test_grosse_bibliothek_mix_trifft_nur_regel(db_ready):
    from hydrahive.db.connection import db
    with db() as conn:
        conn.executemany(
            "INSERT INTO module_radiostream_tracks (track_id, source_id, rel_path, size, mtime, artist, title, genre, "
            "format, duration_s, state, first_seen, last_seen) VALUES (?, 'main', ?, 1, 1, ?, 'T', ?, 'mp3', 200, 'ok', "
            "'x', 'x')", [(f"g{i}", f"K{i}/g{i}.mp3", f"K{i}", "Rock" if i % 50 == 0 else "Pop") for i in range(3000)])
        conn.commit()
    m = program.save_mix(None, name="Rock", rules_={"genres": ["Rock"]}, allow_long=False, user="boss")
    program.set_program("mix", m["id"], user="boss")
    for i in range(30):
        assert int(nxt(i)["track_id"][1:]) % 50 == 0
