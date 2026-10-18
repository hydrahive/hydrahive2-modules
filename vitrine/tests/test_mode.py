"""Umschalten Video ↔ Dashboard: Maus weckt, Rückkehr nach Zeit oder auf Wunsch, kein Flattern."""
from __future__ import annotations

import json

import pytest

from renderer import mode

RET = 120.0


def M(**kw):
    return mode.Mode(return_after=kw.pop("return_after", RET), **kw)


def test_ohne_dashboard_immer_video():
    m = M()
    assert m.update(idle_ms=0, available=False, now=0) == "video"
    assert m.update(idle_ms=None, available=True, now=1) == "video"     # Leerlauf unbekannt → Video


def test_maus_weckt_und_rueckkehr_nach_zeit():
    m = M()
    assert m.update(idle_ms=90_000, available=True, now=0) == "video"
    assert m.update(idle_ms=200, available=True, now=1) == "dashboard"
    assert m.update(idle_ms=60_000, available=True, now=61) == "dashboard"
    assert m.update(idle_ms=RET * 1000 - 1, available=True, now=120.9) == "dashboard"
    assert m.update(idle_ms=RET * 1000, available=True, now=121) == "video"


def test_alte_eingabe_weckt_nicht():
    m = M()
    assert m.update(idle_ms=1500, available=True, now=0) == "video"     # Schwelle 1 s
    assert m.update(idle_ms=999, available=True, now=0.5) == "dashboard"


def test_zurueck_wunsch_und_erst_neue_eingabe_weckt_wieder():
    m = M()
    m.update(idle_ms=0, available=True, now=0)
    assert m.update(idle_ms=300, available=True, now=0.3, back_requested=True) == "video"
    assert m.update(idle_ms=600, available=True, now=0.6) == "video"    # dieselbe Eingabe (Klick auf „Zurück“)
    assert m.update(idle_ms=900, available=True, now=0.9) == "video"
    assert m.update(idle_ms=100, available=True, now=0.85) == "video"    # 0,75 s nach Zurück: noch Karenz (0,5 s) …
    assert m.update(idle_ms=100, available=True, now=1.5) == "dashboard"   # neue Bewegung


def test_klick_auf_zurueck_holt_nicht_selbst_zurueck():
    """Leerlauf ist ganzzahlig in ms: der Klick kann rechnerisch knapp *nach* dem Zurück-Zeitpunkt liegen."""
    m = M()
    m.update(idle_ms=0, available=True, now=10.0)
    assert m.update(idle_ms=0, available=True, now=10.0003, back_requested=True) == "video"
    assert m.update(idle_ms=0, available=True, now=10.0006) == "video"


def test_dashboard_faellt_weg_dann_video():
    m = M()
    m.update(idle_ms=0, available=True, now=0)
    assert m.update(idle_ms=0, available=False, now=1) == "video"


def test_rueckkehrzeit_aenderbar():
    m = M(return_after=30)
    m.update(idle_ms=0, available=True, now=0)
    assert m.update(idle_ms=30_000, available=True, now=30) == "video"


@pytest.mark.parametrize(("raw", "erwartet"), [
    (None, 120), ({"dashboard_return_seconds": 45}, 45), ({"dashboard_return_seconds": 5}, 120),
    ({"dashboard_return_seconds": 7200}, 120), ({"dashboard_return_seconds": "x"}, 120), ({"dashboard_return_seconds": True}, 120),
])
def test_rueckkehrzeit_aus_config(raw, erwartet):
    assert mode.return_seconds(raw or {}) == erwartet


def test_zurueck_datei_wird_einmal_gelesen(tmp_path):
    assert mode.take_back_request(tmp_path) is False
    mode.request_back(tmp_path)
    assert json.loads((tmp_path / "mode.json").read_text())["back"] is True
    assert mode.take_back_request(tmp_path) is True
    assert mode.take_back_request(tmp_path) is False
    (tmp_path / "mode.json").write_text("kaputt")
    assert mode.take_back_request(tmp_path) is False
