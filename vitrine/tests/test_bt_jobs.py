"""S7: Aufträge Backend → Dienst (bt/inbox/*.json) und Stand Dienst → Backend (bt/state.json).

Eigener Ordner `bt/`: `inbox/*.json` gehört den Meldungen (S3), dort würden Aufträge als kaputte Meldung gelöscht.
"""
from __future__ import annotations

import json

import pytest

from renderer import bt_jobs as j

A = "B4:EE:25:ED:70:7F"


def test_auftrag_schreiben_und_lesen_aelteste_zuerst(tmp_path):
    j.put(tmp_path, "scan", now=10.0)
    j.put(tmp_path, "pair", A, now=11.0)
    jobs = j.take(tmp_path)
    assert [(x["kind"], x.get("address")) for x in jobs] == [("scan", None), ("pair", A)]
    assert j.take(tmp_path) == []                                       # abgeholt = weg


@pytest.mark.parametrize("kind, addr", [("pair", None), ("pair", "kaputt"), ("remove", "b4:ee"), ("rm -rf", A),
                                        ("scan", A)])
def test_ungueltige_auftraege_werden_nicht_geschrieben(tmp_path, kind, addr):
    with pytest.raises(j.JobError):
        j.put(tmp_path, kind, addr, now=1.0)
    assert j.take(tmp_path) == []


def test_kaputte_oder_fremde_dateien_werden_verworfen(tmp_path):
    d = tmp_path / "bt" / "inbox"
    d.mkdir(parents=True)
    (d / "1-kaputt.json").write_text("{nicht json")
    (d / "2-fremd.json").write_text(json.dumps({"kind": "pair", "address": "../../x"}))
    (d / "3-art.json").write_text(json.dumps({"kind": "format", "address": A}))
    (d / "4-gut.json").write_text(json.dumps({"kind": "remove", "address": A, "created": 1}))
    assert [(x["kind"], x["address"]) for x in j.take(tmp_path)] == [("remove", A)]
    assert list(d.glob("*.json")) == []                                  # alles aufgeräumt


def test_kleinschreibung_wird_normalisiert(tmp_path):
    j.put(tmp_path, "pair", A.lower(), now=1.0)
    assert j.take(tmp_path)[0]["address"] == A


def test_hoechstens_20_auftraege(tmp_path):
    for i in range(30):
        j.put(tmp_path, "scan", now=float(i))
    assert len(list((tmp_path / "bt" / "inbox").glob("*.json"))) == j.MAX_JOBS == 20


def test_stand_atomar_und_mit_zeit(tmp_path):
    j.write_state(tmp_path, {"window_until": 5.0, "devices": []}, now=100.0)
    s = j.read_state(tmp_path)
    assert s["window_until"] == 5.0 and s["updated"] == 100.0
    assert not list((tmp_path / "bt").glob("*.tmp"))


def test_stand_fehlt_oder_kaputt(tmp_path):
    assert j.read_state(tmp_path) is None
    (tmp_path / "bt").mkdir()
    (tmp_path / "bt" / "state.json").write_text("{kaputt")
    assert j.read_state(tmp_path) is None


def test_meldungen_ordner_bleibt_unberuehrt(tmp_path):
    (tmp_path / "inbox").mkdir()
    (tmp_path / "inbox" / "x.json").write_text("{}")
    j.put(tmp_path, "scan", now=1.0)
    j.take(tmp_path)
    assert (tmp_path / "inbox" / "x.json").exists()


def test_pending_liest_ohne_zu_loeschen(tmp_path):
    assert j.pending(tmp_path, "scan") is False
    j.put(tmp_path, "pair", A, now=1.0)
    assert j.pending(tmp_path, "scan") is False and j.pending(tmp_path, "pair") is True
    (tmp_path / "bt" / "inbox" / "0-kaputt.json").write_text("{x")
    assert j.pending(tmp_path, "pair") is True
    assert len(list((tmp_path / "bt" / "inbox").glob("*.json"))) == 2       # nichts gelöscht
