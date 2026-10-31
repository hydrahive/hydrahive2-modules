"""Programm (PLAN-PROGRAMM.md): Mix-Regeln → SQL-Bedingung. Mehrfach-Genres („Pop;Rock“), Ausschließen, Jahrzehnte,
Ordner, Hörbücher raus aus „Alles“, lange Titel. Gegen eine echte SQLite-Tabelle geprüft."""
from __future__ import annotations

import sqlite3

import pytest
from backend import rules
from backend.rules import RuleError


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE module_radiostream_tracks (track_id TEXT, rel_path TEXT, artist TEXT, album_artist TEXT, "
              "genre TEXT, year INTEGER, duration_s REAL, state TEXT)")
    rows = [
        ("rock80", "AC_DC/Back in Black/01.mp3", "AC/DC", "", "Hard Rock;Rock", 1980, 250, "ok"),
        ("pop90", "Madonna/x.mp3", "Madonna", "", "Pop", 1990, 240, "ok"),
        ("poprock", "Bowie/x.mp3", "David Bowie", "", "Pop; Rock", 1983, 260, "ok"),
        ("rockabilly", "Cash/x.mp3", "Johnny Cash", "Johnny Cash", "Rockabilly", 1956, 150, "ok"),
        ("bibi", "Bibi Blocksberg/Folge 1.mp3", "Bibi Blocksberg", "", "Kids; Audiobooks; Audiobooks in German",
         1990, 2400, "ok"),
        ("hoerspiel", "TKKG/1.mp3", "Stefan Wolf", "", "Hörspiel", 1985, 3000, "ok"),
        ("lang", "Pink Floyd/Echoes.flac", "Pink Floyd", "", "Progressive Rock", 1971, 1400, "ok"),
        ("ohne", "Unbekannt/x.mp3", "", "", "", None, None, "ok"),
        ("weg", "Weg/x.mp3", "Weg", "", "Rock", 1990, 200, "missing"),
        ("acdc2", "AC_DC/Live/02.mp3", "", "AC/DC", "Rock", 1992, 300, "ok"),
    ]
    c.executemany("INSERT INTO module_radiostream_tracks VALUES (?,?,?,?,?,?,?,?)", rows)
    return c


def ids(conn, rule: dict, exclude: dict | None = None, allow_long: bool = False) -> set[str]:
    where, args = rules.where(rule, exclude=exclude or {}, allow_long=allow_long)
    return {r[0] for r in conn.execute(f"SELECT track_id FROM module_radiostream_tracks t WHERE {where}", args)}


def test_leer_alles_ohne_fehlende_und_ohne_lange(conn):
    """Leere Regel = alle Titel im Zustand ok, ohne lange (bibi/hoerspiel/lang sind > 15 min)."""
    assert ids(conn, {}) == {"rock80", "pop90", "poprock", "rockabilly", "ohne", "acdc2"}


def test_lange_nur_wenn_erlaubt(conn):
    assert "lang" not in ids(conn, {}) and "bibi" not in ids(conn, {})
    assert {"lang", "bibi", "hoerspiel"} <= ids(conn, {}, allow_long=True)
    assert "ohne" in ids(conn, {})                                   # unbekannte Dauer gilt nicht als lang


def test_genre_einzeln_aus_mehrfachfeld(conn):
    assert ids(conn, {"genres": ["Rock"]}) == {"rock80", "poprock", "acdc2"}
    assert ids(conn, {"genres": ["rock"]}) == {"rock80", "poprock", "acdc2"}          # Groß/klein egal
    assert ids(conn, {"genres": ["Pop"]}) == {"pop90", "poprock"}


def test_genre_kein_teilwort(conn):
    """„Rock“ trifft nicht „Rockabilly“ oder „Hard Rock“ als Ganzes – nur das Genre „Rock“."""
    assert "rockabilly" not in ids(conn, {"genres": ["Rock"]})
    assert ids(conn, {"genres": ["Hard Rock"]}) == {"rock80"}


def test_mehrere_genres_oder(conn):
    assert ids(conn, {"genres": ["Pop", "Rockabilly"]}) == {"pop90", "poprock", "rockabilly"}


def test_interpret_auch_album_interpret(conn):
    assert ids(conn, {"artists": ["AC/DC"]}) == {"rock80", "acdc2"}
    assert ids(conn, {"artists": ["ac/dc"]}) == {"rock80", "acdc2"}


def test_jahrzehnte(conn):
    assert ids(conn, {"decades": [1980]}) == {"rock80", "poprock"}
    assert ids(conn, {"decades": [1950, 1990]}) == {"rockabilly", "pop90", "acdc2"}


def test_jahr_von_bis(conn):
    assert ids(conn, {"year_from": 1983, "year_to": 1990}) == {"poprock", "pop90"}


def test_ordner(conn):
    assert ids(conn, {"folders": ["AC_DC"]}) == {"rock80", "acdc2"}
    assert ids(conn, {"folders": ["AC_"]}) == set()                  # ganzer Ordnername, kein Anfang


def test_ordner_mit_platzhalterzeichen(conn):
    conn.execute("INSERT INTO module_radiostream_tracks VALUES ('pct','50%_Hits/x.mp3','x','','Pop',2000,200,'ok')")
    assert ids(conn, {"folders": ["50%_Hits"]}) == {"pct"}
    assert ids(conn, {"folders": ["5%"]}) == set()


def test_bedingungen_und_verknuepft(conn):
    assert ids(conn, {"genres": ["Rock"], "decades": [1980]}) == {"rock80", "poprock"}


def test_ausschliessen(conn):
    assert ids(conn, {"genres": ["Rock"], "exclude_artists": ["David Bowie"]}) == {"rock80", "acdc2"}
    assert ids(conn, {"genres": ["Rock"], "exclude_folders": ["AC_DC"]}) == {"poprock"}
    assert ids(conn, {"exclude_genres": ["Pop"]}) == {"rock80", "rockabilly", "ohne", "acdc2"}


def test_ausschluss_alles_hoerbuecher(conn):
    exclude = {"genres": rules.DEFAULT_EXCLUDE["genres"]}
    got = ids(conn, {}, exclude=exclude, allow_long=True)
    assert "bibi" not in got and "hoerspiel" not in got and "lang" in got


def test_voreinstellung_hoerbuecher_als_wortteil():
    """Hörbuch-Genres heißen sehr unterschiedlich – Voreinstellung trifft Wortteile."""
    for g in ("Kids; Audiobooks; Audiobooks in German", "Hörbuch", "Hörspiel", "Spoken Word", "Audiobook"):
        assert rules.matches_default_exclude(g), g
    for g in ("Rock", "Pop", "Kids", "Speak Softly"):
        assert not rules.matches_default_exclude(g), g


def test_nur_ok(conn):
    assert "weg" not in ids(conn, {"genres": ["Rock"]})


@pytest.mark.parametrize("rule", [
    {"genres": "Rock"}, {"genres": [1]}, {"decades": [1985]}, {"decades": [3000]}, {"year_from": "x"},
    {"genres": ["x" * 201]}, {"genres": ["a"] * 101}, {"unbekannt": []}, {"folders": ["a/b"]}, {"folders": [""]},
])
def test_ungueltige_regel(rule):
    with pytest.raises(RuleError, match="^radiostream_rule_invalid$"):
        rules.validate(rule)


def test_gueltige_regel_wird_bereinigt():
    assert rules.validate({"genres": [" Rock ", "rock"], "decades": [1980]}) == {"genres": ["Rock"], "decades": [1980]}


def test_keine_einschleusung(conn):
    evil = "Rock'); DROP TABLE module_radiostream_tracks; --"
    ids(conn, {"genres": [evil], "artists": [evil], "folders": ["x'y"]})
    assert conn.execute("SELECT count(*) FROM module_radiostream_tracks").fetchone()[0] == 10
