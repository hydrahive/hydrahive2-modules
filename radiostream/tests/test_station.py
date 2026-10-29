"""Sender-Einstellungen (PLAN-E2.md, Till 29.10.: alles in der Oberfläche einstellbar)."""
from __future__ import annotations

import pytest
from backend import station


def test_voreinstellungen(db_ready):
    assert station.get() == {"name": "Radiostream", "subtitle": "", "artist_gap_min": 60, "title_gap_days": 3,
                             "listen_port": 8800, "reach": "all", "max_listeners": 50}


def test_speichern_und_lesen(db_ready):
    out = station.save(user="boss", name="  Tills   Radio ", subtitle="Rund um die Uhr", listen_port=8900,
                       reach="home", max_listeners=20, artist_gap_min=30, title_gap_days=7)
    assert out == {"name": "Tills Radio", "subtitle": "Rund um die Uhr", "artist_gap_min": 30, "title_gap_days": 7,
                   "listen_port": 8900, "reach": "home", "max_listeners": 20}


def test_teilweise_speichern_behaelt_den_rest(db_ready):
    station.save(user="boss", name="A", listen_port=8900)
    out = station.save(user="boss", subtitle="B")
    assert out["name"] == "A" and out["listen_port"] == 8900 and out["subtitle"] == "B"


@pytest.mark.parametrize("port", [80, 443, 1023, 8001, 8810, 3001, 65536, 0, "8800"])
def test_port_abgelehnt(db_ready, port):
    with pytest.raises(station.StationError) as e:
        station.save(user="boss", listen_port=port)
    assert e.value.code == "radiostream_port_invalid"


@pytest.mark.parametrize(("key", "value"), [("reach", "internet"), ("max_listeners", 0), ("max_listeners", 1001),
                                             ("artist_gap_min", -1), ("title_gap_days", 61), ("name", "   "),
                                             ("unbekannt", 1)])
def test_ungueltig(db_ready, key, value):
    with pytest.raises(station.StationError) as e:
        station.save(user="boss", **{key: value})
    assert e.value.code == "radiostream_station_invalid"


def test_name_hoechstens_80_zeichen(db_ready):
    assert len(station.save(user="boss", name="x" * 200)["name"]) == 80


def test_wahr_falsch_ist_keine_zahl(db_ready):
    """True ist in Python auch 1 – das darf nicht als Hörerzahl 1 durchgehen."""
    with pytest.raises(station.StationError):
        station.save(user="boss", max_listeners=True)
