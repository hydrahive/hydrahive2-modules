"""S7: Backend-Seite Bluetooth – Stand lesen, Aufträge nur unter den Regeln der Spec."""
from __future__ import annotations

import pytest

from backend import bluetooth as bt
from renderer import bt_jobs

A3, A4 = "B4:EE:25:ED:70:7F", "B4:EE:25:EE:72:7F"
NOW = 1000.0


def _state(tmp, *, window_until=NOW + 60, updated=NOW, devices=None, **kw):
    devices = devices if devices is not None else [
        {"address": A3, "name": "RAPOO BT3.0 KB", "rssi": -62, "icon": "input-keyboard", "le": False},
        {"address": A4, "name": "RAPOO BT4.0 KB", "rssi": -58, "icon": "input-keyboard", "le": True},
    ]
    bt_jobs.write_state(tmp, {"adapter": {"name": "hydrahive-master", "powered": True}, "window_until": window_until,
                              "devices": devices, **kw}, now=updated)


def test_ohne_dienst_nicht_verfuegbar(tmp_path):
    v = bt.view(tmp_path, now=NOW)
    assert v["available"] is False and v["devices"] == []


def test_alter_stand_gilt_als_nicht_verfuegbar(tmp_path):
    _state(tmp_path, updated=NOW - bt.STALE_SECONDS - 1)
    assert bt.view(tmp_path, now=NOW)["available"] is False


def test_ansicht_fasst_zwillinge_zusammen_und_zeigt_restzeit(tmp_path):
    _state(tmp_path)
    v = bt.view(tmp_path, now=NOW)
    assert v["available"] is True and v["window_left"] == 60
    assert len(v["devices"]) == 1 and v["devices"][0]["addresses"] == [A3, A4]
    assert v["weak_signal"] is False


def test_ansicht_zeigt_code_nur_bei_laufender_kopplung(tmp_path):
    _state(tmp_path, pairing={"address": A3, "passkey": "123456"})
    assert bt.view(tmp_path, now=NOW)["pairing"] == {"address": A3, "passkey": "123456"}
    _state(tmp_path, pairing={"address": A3, "passkey": "12x456"})          # kein 6-stelliger Code → keiner
    assert bt.view(tmp_path, now=NOW)["pairing"] == {"address": A3, "passkey": None}


def test_geschlossenes_fenster_restzeit_null(tmp_path):
    _state(tmp_path, window_until=NOW - 1)
    assert bt.view(tmp_path, now=NOW)["window_left"] == 0


def test_scan_legt_auftrag_an_aber_nicht_doppelt(tmp_path):
    _state(tmp_path, window_until=0)
    assert bt.scan(tmp_path, now=NOW) == {"started": True}
    assert bt.scan(tmp_path, now=NOW + 1) == {"started": False}              # Auftrag liegt schon da
    assert [x["kind"] for x in bt_jobs.take(tmp_path)] == ["scan"]
    _state(tmp_path, window_until=NOW + 30)
    assert bt.scan(tmp_path, now=NOW) == {"started": False}                  # Fenster schon offen → nicht verlängern
    assert bt_jobs.take(tmp_path) == []


def test_scan_ohne_dienst(tmp_path):
    with pytest.raises(bt.BtError) as e:
        bt.scan(tmp_path, now=NOW)
    assert e.value.code == "unavailable"


def test_pair_regeln(tmp_path):
    _state(tmp_path)
    with pytest.raises(bt.BtError) as e:
        bt.pair(tmp_path, "kaputt", now=NOW)
    assert e.value.code == "invalid_address"
    with pytest.raises(bt.BtError) as e:
        bt.pair(tmp_path, "AA:AA:AA:AA:AA:AA", now=NOW)
    assert e.value.code == "not_seen"
    _state(tmp_path, window_until=NOW - 1)
    with pytest.raises(bt.BtError) as e:
        bt.pair(tmp_path, A3, now=NOW)
    assert e.value.code == "window_closed"
    assert bt_jobs.take(tmp_path) == []


def test_pair_legt_auftrag_an(tmp_path):
    _state(tmp_path)
    bt.pair(tmp_path, A4.lower(), now=NOW)
    assert [(x["kind"], x["address"]) for x in bt_jobs.take(tmp_path)] == [("pair", A4)]


def test_entfernen_nur_gekoppelte(tmp_path):
    _state(tmp_path, devices=[{"address": A3, "name": "RAPOO BT3.0 KB", "paired": True},
                              {"address": A4, "name": "RAPOO BT4.0 KB", "paired": False}])
    bt.remove(tmp_path, A3, now=NOW)
    assert [(x["kind"], x["address"]) for x in bt_jobs.take(tmp_path)] == [("remove", A3)]
    with pytest.raises(bt.BtError) as e:
        bt.remove(tmp_path, A4, now=NOW)                                  # gesehen, aber nicht gekoppelt
    assert e.value.code == "not_paired"
    with pytest.raises(bt.BtError) as e:
        bt.remove(tmp_path, "AA:AA:AA:AA:AA:AA", now=NOW)                 # gar nicht bekannt
    assert e.value.code == "not_paired"
    assert bt_jobs.take(tmp_path) == []
