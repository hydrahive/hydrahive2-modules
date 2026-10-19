"""S4 Zuhause: HA-Favoriten je Raum, nur über den Client des HA-Moduls (SPEC-STATUSZENTRALE.md, S4)."""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager

import pytest

from backend import dash_home as dh

FAV = """CREATE TABLE module_homeassistant_favorites (id INTEGER PRIMARY KEY, "user" TEXT, entity_id TEXT,
         sort INTEGER DEFAULT 0, created_at TEXT DEFAULT '');"""


def _db(tmp_path, rows=None, table=True):
    path = tmp_path / "t.db"
    con = sqlite3.connect(path)
    if table:
        con.executescript(FAV)
        for i, (u, e) in enumerate(rows or []):
            con.execute('INSERT INTO module_homeassistant_favorites ("user", entity_id, sort) VALUES (?,?,?)', (u, e, i))
    con.commit()
    con.close()

    @contextmanager
    def connect():
        c = sqlite3.connect(path)
        c.row_factory = sqlite3.Row
        try:
            yield c
        finally:
            c.close()
    return connect


def _ent(eid, area, dc, state, unit="", age=60, name=None):
    return {"id": eid, "name": name or eid, "area": area, "dc": dc, "state": state, "unit": unit, "age": age}


class FakeHA:
    def __init__(self, ents=None, exc=None):
        self.templates, self.ents, self.exc = [], ents or [], exc

    async def render_template(self, template):
        self.templates.append(template)
        if self.exc:
            raise self.exc
        return json.dumps(self.ents)


ROWS = [("till", "sensor.wz_temp"), ("till", "sensor.wz_hum"), ("till", "sensor.wz_bat"),
        ("till", "sensor.ku_temp"), ("till", "sensor.alex_temp"), ("till", "sensor.alex_energy"),
        ("anna", "sensor.fremd")]
ENTS = [_ent("sensor.wz_temp", "Wohnzimmer", "temperature", "22.4", "°C"),
        _ent("sensor.wz_hum", "Wohnzimmer", "humidity", "53.0", "%"),
        _ent("sensor.wz_bat", "Wohnzimmer", "battery", "80.0", "%"),
        _ent("sensor.ku_temp", "Küche", "temperature", "23.1", "°C"),
        _ent("sensor.alex_temp", "Alex Zimmer", "temperature", "unavailable", "°C", age=46900),
        _ent("sensor.alex_energy", "Alex Zimmer", "energy", "unavailable", "kWh", age=46000)]


def test_raeume_in_favoriten_reihenfolge():
    ha = FakeHA(ENTS)
    r = dh.home("till", rooms=[], connect=_db_cache["c"], client=ha)
    assert [x["room"] for x in r["rooms"]] == ["Wohnzimmer", "Küche", "Alex Zimmer"]
    wz = r["rooms"][0]
    assert wz["temp"] == "22,4 °C" and wz["hum"] == "53 %" and wz["battery_low"] is None and wz["offline_h"] is None
    assert r["rooms"][1]["hum"] is None


def test_alle_werte_weg_raum_grau_mit_stunden():
    r = dh.home("till", rooms=[], connect=_db_cache["c"], client=FakeHA(ENTS))
    alex = r["rooms"][2]
    assert alex["offline_h"] == 12 and alex["temp"] is None and alex["extra"] is None, "jüngste Änderung zählt (46000 s)"


@pytest.mark.parametrize(("bat", "zeigen"), [("19.0", "19 %"), ("20.0", None), ("5", "5 %"), ("unavailable", None)])
def test_batterie_nur_unter_20(bat, zeigen):
    ents = [_ent("sensor.wz_temp", "Wohnzimmer", "temperature", "22.4", "°C"),
            _ent("sensor.wz_bat", "Wohnzimmer", "battery", bat, "%")]
    r = dh.home("till", rooms=[], connect=_db_cache["c"], client=FakeHA(ents))
    assert r["rooms"][0]["battery_low"] == zeigen


def test_weiterer_wert_kurz_am_ende():
    ents = [_ent("sensor.alex_energy", "Alex Zimmer", "energy", "12.345", "kWh")]
    r = dh.home("till", rooms=[], connect=_db_cache["c"], client=FakeHA(ents))
    assert r["rooms"][0]["extra"] == "12,3 kWh" and r["rooms"][0]["offline_h"] is None


def test_ohne_raum_sonstiges_und_raumauswahl():
    ents = ENTS + [_ent("sensor.ku_temp", "", "temperature", "23.1", "°C")]
    r = dh.home("till", rooms=[], connect=_db_cache["c"], client=FakeHA(ents[-1:] + ENTS[:3]))
    assert [x["room"] for x in r["rooms"]] == ["Wohnzimmer", "Sonstiges"]
    r = dh.home("till", rooms=["Küche"], connect=_db_cache["c"], client=FakeHA(ENTS))
    assert [x["room"] for x in r["rooms"]] == ["Küche"]


def test_template_nur_mit_eigenen_geprueften_ids(tmp_path):
    tmp_path = tmp_path / "eigen"
    tmp_path.mkdir()
    rows = [("till", "sensor.ok_1"), ("till", "sensor.x\"}}{{ 7*7 }}"), ("till", "Sensor.GROSS"), ("anna", "sensor.fremd")]
    ha = FakeHA([])
    dh.home("till", rooms=[], connect=_db(tmp_path, rows), client=ha)
    [t] = ha.templates
    assert "sensor.ok_1" in t and "7*7" not in t and "GROSS" not in t and "fremd" not in t


def test_ohne_favoriten_kein_ha_aufruf(tmp_path):
    tmp_path = tmp_path / "leer"
    tmp_path.mkdir()
    ha = FakeHA(ENTS)
    assert dh.home("till", rooms=[], connect=_db(tmp_path, []), client=ha) == {"rooms": [], "error": None}
    assert ha.templates == []


def test_tabelle_fehlt_oder_modul_fehlt_none(tmp_path):
    tmp_path = tmp_path / "ohne"
    tmp_path.mkdir()
    assert dh.home("till", rooms=[], connect=_db(tmp_path, table=False), client=FakeHA(ENTS)) is None
    assert dh.home("till", rooms=[], connect=_db_cache["c"], client=None) is None


def test_ha_fehler_wird_text():
    r = dh.home("till", rooms=[], connect=_db_cache["c"], client=FakeHA(exc=RuntimeError("HTTP 401 token xyz")))
    assert r == {"rooms": [], "error": "Home Assistant nicht erreichbar"}
    r = dh.home("till", rooms=[], connect=_db_cache["c"], client=FakeHA())
    assert r["rooms"] == []


def test_hoechstens_50_favoriten(tmp_path):
    tmp_path = tmp_path / "viele"
    tmp_path.mkdir()
    rows = [("till", f"sensor.s{i}") for i in range(80)]
    ha = FakeHA([])
    dh.home("till", rooms=[], connect=_db(tmp_path, rows), client=ha)
    assert ha.templates[0].count('"sensor.s') == dh.MAX_FAVORITES == 50


def test_client_aus_geladenem_ha_modul(monkeypatch):
    import sys
    import types
    fake = types.ModuleType("hhmod_homeassistant")
    fake.client = object()
    monkeypatch.setitem(sys.modules, "hhmod_homeassistant", fake)
    assert dh.ha_client() is fake.client
    monkeypatch.delitem(sys.modules, "hhmod_homeassistant")
    assert dh.ha_client() is None


_db_cache: dict = {}


@pytest.fixture(autouse=True)
def _standard_db(tmp_path):
    _db_cache["c"] = _db(tmp_path, ROWS)
    yield
