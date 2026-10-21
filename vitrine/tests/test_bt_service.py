"""S7: Dienst – Fenster öffnen/schließen (120 s), Start räumt auf, bt_busy, BlueZ-Netz."""
from __future__ import annotations

import pytest  # noqa: F401 - parametrize in einzelnen Tests

from _bt_fake import A3, A4, RAPOO, FakeBluez, run, svc  # noqa: F401
from renderer import bt_jobs, bt_service


def test_start_schliesst_alles(tmp_path):
    fake = FakeBluez()
    s, _ = svc(tmp_path, fake)
    run(s.start())
    assert fake.props["Pairable"] is False and fake.props["Discoverable"] is False
    assert fake.discovering is False and fake.agent is False
    assert bt_jobs.read_state(tmp_path)["window_until"] == 0


def test_fenster_oeffnen_und_nach_120s_schliessen(tmp_path):
    fake = FakeBluez(RAPOO)
    s, clock = svc(tmp_path, fake)
    run(s.start())
    fake.calls.clear()
    bt_jobs.put(tmp_path, "scan", now=clock["t"])
    run(s.tick())
    assert ("set", "Powered", True) in fake.calls and ("set", "Pairable", True) in fake.calls
    assert ("set", "Discoverable", True) in fake.calls and fake.discovering and fake.agent
    st = bt_jobs.read_state(tmp_path)
    assert st["window_until"] == clock["t"] + bt_service.WINDOW_SECONDS == 1120.0
    assert {d["address"] for d in st["devices"]} == {A3, A4}
    clock["t"] += bt_service.WINDOW_SECONDS - 1
    run(s.tick())
    assert fake.discovering is True                                      # noch offen
    clock["t"] += 2
    run(s.tick())
    assert fake.props["Pairable"] is False and fake.props["Discoverable"] is False
    assert fake.discovering is False and fake.agent is False
    assert bt_jobs.read_state(tmp_path)["window_until"] == 0


def test_zweiter_scan_verlaengert_nicht(tmp_path):
    fake = FakeBluez(RAPOO)
    s, clock = svc(tmp_path, fake)
    run(s.start())
    bt_jobs.put(tmp_path, "scan", now=clock["t"])
    run(s.tick())
    clock["t"] += 60
    bt_jobs.put(tmp_path, "scan", now=clock["t"])
    run(s.tick())
    assert bt_jobs.read_state(tmp_path)["window_until"] == 1120.0


def test_bluez_fehler_beim_lesen_stoppt_nicht(tmp_path):
    fake = FakeBluez(RAPOO)

    async def kaputt():
        raise bt_service.BluezError("org.freedesktop.DBus.Error.ServiceUnknown")

    fake.devices_list = kaputt
    s, clock = svc(tmp_path, fake)
    run(s.start())
    run(s.tick())
    st = bt_jobs.read_state(tmp_path)
    assert st["devices"] == [] and "ServiceUnknown" in st["error"]


@pytest.mark.parametrize("busy", [True, False])
def test_busy_datei_nur_bei_offenem_fenster(tmp_path, busy):
    fake = FakeBluez(RAPOO)
    s, clock = svc(tmp_path, fake)
    run(s.start())
    if busy:
        bt_jobs.put(tmp_path, "scan", now=clock["t"])
    run(s.tick())
    assert (tmp_path / bt_service.BUSY_FILE).exists() is busy



def test_busy_datei_verschwindet_wenn_fenster_zu(tmp_path):
    fake = FakeBluez(RAPOO)
    s, clock = svc(tmp_path, fake)
    run(s.start())
    bt_jobs.put(tmp_path, "scan", now=clock["t"])
    run(s.tick())
    assert (tmp_path / bt_service.BUSY_FILE).exists()
    clock["t"] += bt_service.WINDOW_SECONDS + 1
    run(s.tick())
    assert not (tmp_path / bt_service.BUSY_FILE).exists()


def test_start_raeumt_alte_busy_datei_weg(tmp_path):
    (tmp_path / bt_service.BUSY_FILE).write_text('{"since": 1}')
    s, _ = svc(tmp_path, FakeBluez())
    run(s.start())
    assert not (tmp_path / bt_service.BUSY_FILE).exists()


def test_bluez_schliesst_selbst_falls_der_dienst_stirbt(tmp_path):
    """Harter Abbruch (Update, Absturz) bei offenem Fenster: BlueZ-Timeouts schließen spätestens nach 180 s."""
    fake = FakeBluez(RAPOO)
    s, clock = svc(tmp_path, fake)
    run(s.start())
    bt_jobs.put(tmp_path, "scan", now=clock["t"])
    run(s.tick())
    t = [c for c in fake.calls if c[0] == "timeouts"]
    assert t and t[0][1] == 180
    i_t = fake.calls.index(t[0])
    i_p = fake.calls.index(("set", "Pairable", True))
    assert i_t < i_p, "Timeout vor dem Öffnen setzen"
