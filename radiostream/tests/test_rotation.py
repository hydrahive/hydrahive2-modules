"""AutoDJ-Rotation (PLAN-E2.md „Rotation“): Künstler frühestens nach 60 min, Titel frühestens nach 3 Tagen,
nur Titel im Zustand ok, nie Stille – bei Bedarf Sperren schrittweise lockern."""
from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta

import pytest
from backend import rotation

T0 = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)


def _add(track_id, artist, title="T", state="ok", album_artist=""):
    from hydrahive.db.connection import db
    with db() as conn:
        conn.execute(
            "INSERT INTO module_radiostream_tracks (track_id, source_id, rel_path, size, mtime, artist, album_artist, "
            "title, format, state, first_seen, last_seen) VALUES (?, 'main', ?, 1, 1, ?, ?, ?, 'mp3', ?, 'x', 'x')",
            (track_id, f"{artist}/{track_id}.mp3", artist, album_artist, title, state))
        conn.commit()


def _played(track_id, artist, at):
    rotation.record(track_id, artist, at=at)


def test_waehlt_nur_titel_im_zustand_ok(db_ready):
    _add("a", "Queen", state="missing")
    _add("b", "Queen", state="error")
    _add("c", "ABBA")
    for _ in range(20):
        assert rotation.pick(now=T0, rng=random.Random(_))["track_id"] == "c"


def test_kuenstlersperre_60_minuten(db_ready):
    _add("q1", "Queen")
    _add("q2", "Queen")
    _add("a1", "ABBA")
    _played("q1", "Queen", T0 - timedelta(minutes=59))
    for i in range(30):
        assert rotation.pick(now=T0, rng=random.Random(i))["track_id"] == "a1"


def test_kuenstler_nach_61_minuten_wieder_erlaubt(db_ready):
    _add("q1", "Queen")
    _add("q2", "Queen")
    _played("q1", "Queen", T0 - timedelta(minutes=61))
    assert rotation.pick(now=T0, rng=random.Random(1))["track_id"] == "q2"


def test_titelsperre_3_tage(db_ready):
    _add("q1", "Queen")
    _add("a1", "ABBA")
    _played("q1", "Queen", T0 - timedelta(days=2, hours=23))
    _played("a1", "ABBA", T0 - timedelta(days=3, minutes=5))
    for i in range(20):
        assert rotation.pick(now=T0, rng=random.Random(i))["track_id"] == "a1"


def test_kuenstler_gross_klein_und_leerzeichen_egal(db_ready):
    """„QUEEN “ und „Queen“ sind derselbe Künstler; ohne Künstler zählt der Albumkünstler."""
    _add("q1", "QUEEN ")
    _add("a1", "ABBA")
    _add("x1", "", album_artist="Queen")
    _played("q9", "Queen", T0 - timedelta(minutes=10))
    for i in range(20):
        assert rotation.pick(now=T0, rng=random.Random(i))["track_id"] == "a1"


def test_ohne_freien_titel_wird_gelockert_nie_stille(db_ready):
    """Nur ein Künstler mit einem Titel, eben gespielt → trotzdem kommt etwas (lieber Wiederholung als Stille)."""
    _add("q1", "Queen")
    _played("q1", "Queen", T0 - timedelta(minutes=1))
    got = rotation.pick(now=T0, rng=random.Random(0))
    assert got["track_id"] == "q1" and got["relaxed"] is True


def test_lockern_zuerst_kuenstler_dann_titel(db_ready):
    """Ist der Künstler gesperrt, aber der Titel frei, gewinnt der freie Titel vor einer Titelwiederholung."""
    _add("q1", "Queen")
    _add("q2", "Queen")
    _played("q1", "Queen", T0 - timedelta(minutes=5))
    for i in range(20):
        got = rotation.pick(now=T0, rng=random.Random(i))
        assert got["track_id"] == "q2" and got["relaxed"] is True


def test_normalfall_nicht_gelockert(db_ready):
    _add("a1", "ABBA")
    assert rotation.pick(now=T0, rng=random.Random(0))["relaxed"] is False


def test_leere_bibliothek(db_ready):
    _add("a", "Queen", state="missing")
    with pytest.raises(rotation.NothingToPlay):
        rotation.pick(now=T0, rng=random.Random(0))


def test_sperren_aus_den_einstellungen(db_ready):
    from backend import station
    station.save(artist_gap_min=10, title_gap_days=1, user="boss")
    _add("q1", "Queen")
    _add("q2", "Queen")
    _add("a1", "ABBA")
    _played("q1", "Queen", T0 - timedelta(minutes=11))
    seen = {rotation.pick(now=T0, rng=random.Random(i))["track_id"] for i in range(40)}
    assert "q2" in seen


def test_verteilung_zufaellig_ueber_viele_titel(db_ready):
    for i in range(200):
        _add(f"t{i}", f"Kuenstler {i}")
    seen = {rotation.pick(now=T0, rng=random.Random(i))["track_id"] for i in range(50)}
    assert len(seen) > 35


def test_gespielt_liste_wird_nach_30_tagen_aufgeraeumt(db_ready):
    _played("alt", "X", T0 - timedelta(days=31))
    _played("neu", "Y", T0 - timedelta(days=29))
    rotation.prune(now=T0)
    assert [p["track_id"] for p in rotation.recent(limit=10)] == ["neu"]


def test_zuletzt_gespielt_neueste_zuerst(db_ready):
    _add("a1", "ABBA", title="Waterloo")
    _add("q1", "Queen", title="One Vision")
    _played("a1", "ABBA", T0 - timedelta(minutes=10))
    _played("q1", "Queen", T0 - timedelta(minutes=2))
    r = rotation.recent(limit=5)
    assert [(x["track_id"], x["artist"], x["title"]) for x in r] == [("q1", "Queen", "One Vision"),
                                                                     ("a1", "ABBA", "Waterloo")]


def test_grosse_bibliothek_waehlt_nie_fehlende(db_ready):
    """Ab einer gewissen Größe wird per Stichprobe gewählt – auch dort nie ‚missing‘ (sonst Stille im Sender)."""
    from hydrahive.db.connection import db
    with db() as conn:
        conn.executemany(
            "INSERT INTO module_radiostream_tracks (track_id, source_id, rel_path, size, mtime, artist, title, format, "
            "state, first_seen, last_seen) VALUES (?, 'main', ?, 1, 1, ?, 'T', 'mp3', ?, 'x', 'x')",
            [(f"g{i}", f"K{i}/g{i}.mp3", f"K{i}", "ok" if i % 10 == 0 else "missing") for i in range(2000)])
        conn.commit()
    for i in range(40):
        got = rotation.pick(now=T0, rng=random.Random(i))
        assert int(got["track_id"][1:]) % 10 == 0, got
