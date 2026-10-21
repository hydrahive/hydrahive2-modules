"""S7: Dienst – Koppeln (klassisch zuerst, dann LE), Code, nur Gesehenes, Entfernen, Meldungen."""
from __future__ import annotations

import pytest  # noqa: F401 - parametrize in einzelnen Tests

from _bt_fake import A3, A4, RAPOO, FakeBluez, run, svc  # noqa: F401
from renderer import bt_jobs, bt_service


def test_koppeln_klassisch_zuerst_dann_trust_connect_meldung(tmp_path):
    fake = FakeBluez(RAPOO)
    s, clock = svc(tmp_path, fake)
    run(s.start())
    bt_jobs.put(tmp_path, "scan", now=clock["t"])
    run(s.tick())
    fake.calls.clear()
    bt_jobs.put(tmp_path, "pair", A4, now=clock["t"])                   # angetippt wurde die LE-Adresse
    run(s.tick())
    assert [c for c in fake.calls if c[0] in ("pair", "trust", "connect")] == [
        ("pair", A3), ("trust", A3), ("connect", A3)]
    assert s.notes == [("Bluetooth: RAPOO KB gekoppelt", "success")]
    assert fake.props["Pairable"] is False                               # nach Erfolg sofort zu


def test_klassisch_scheitert_dann_le(tmp_path):
    fake = FakeBluez(RAPOO, fail_pair={A3})
    s, clock = svc(tmp_path, fake)
    run(s.start())
    bt_jobs.put(tmp_path, "scan", now=clock["t"])
    run(s.tick())
    fake.calls.clear()
    bt_jobs.put(tmp_path, "pair", A3, now=clock["t"])
    run(s.tick())
    assert [c for c in fake.calls if c[0] == "pair"] == [("pair", A3), ("pair", A4)]
    assert ("connect", A4) in fake.calls


def test_beide_scheitern_fehler_im_stand_fenster_bleibt_offen(tmp_path):
    fake = FakeBluez(RAPOO, fail_pair={A3, A4})
    s, clock = svc(tmp_path, fake)
    run(s.start())
    bt_jobs.put(tmp_path, "scan", now=clock["t"])
    run(s.tick())
    bt_jobs.put(tmp_path, "pair", A3, now=clock["t"])
    run(s.tick())
    st = bt_jobs.read_state(tmp_path)
    assert "nicht gekoppelt" in st["error"] and st["pairing"] is None
    assert st["window_until"] > clock["t"] and s.notes == []             # nochmal versuchen möglich


def test_koppeln_bei_geschlossenem_fenster_tut_nichts(tmp_path):
    fake = FakeBluez(RAPOO)
    s, clock = svc(tmp_path, fake)
    run(s.start())
    fake.calls.clear()
    bt_jobs.put(tmp_path, "pair", A3, now=clock["t"])
    run(s.tick())
    assert not [c for c in fake.calls if c[0] == "pair"]


def test_code_erscheint_waehrend_des_koppelns_und_verschwindet(tmp_path):
    fake = FakeBluez(RAPOO)
    s, clock = svc(tmp_path, fake)
    seen = {}

    async def show(addr):
        s.agent.display_passkey(addr, 123456)                             # BlueZ ruft DisplayPasskey am Agenten
        seen["state"] = bt_jobs.read_state(tmp_path)

    fake.on_pair = show
    run(s.start())
    bt_jobs.put(tmp_path, "scan", now=clock["t"])
    run(s.tick())
    bt_jobs.put(tmp_path, "pair", A3, now=clock["t"])
    run(s.tick())
    assert seen["state"]["pairing"] == {"address": A3, "passkey": "123456"}
    assert bt_jobs.read_state(tmp_path)["pairing"] is None


def test_entfernen_auch_ohne_fenster_und_meldung(tmp_path):
    fake = FakeBluez([dict(RAPOO[0], paired=True)])
    s, clock = svc(tmp_path, fake)
    run(s.start())
    bt_jobs.put(tmp_path, "remove", A3, now=clock["t"])
    run(s.tick())
    assert ("remove", A3) in fake.calls and s.notes == [("Bluetooth: RAPOO BT3.0 KB entfernt", "info")]


def test_ungesehenes_geraet_wird_nicht_gekoppelt(tmp_path):
    """Auch wenn ein Auftrag am Backend vorbei in bt/inbox landet: nur Geräte, die die Suche sieht."""
    fake = FakeBluez(RAPOO)
    s, clock = svc(tmp_path, fake)
    run(s.start())
    bt_jobs.put(tmp_path, "scan", now=clock["t"])
    run(s.tick())
    fake.calls.clear()
    bt_jobs.put(tmp_path, "pair", "AA:AA:AA:AA:AA:AA", now=clock["t"])
    run(s.tick())
    assert not [c for c in fake.calls if c[0] == "pair"]
