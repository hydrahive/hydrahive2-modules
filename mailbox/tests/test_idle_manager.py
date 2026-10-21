"""M2 Schritt 9 (Teil 2): Aufseher für IDLE-Threads – je Konto genau einer, gelöschte Konten beenden,
„unsupported“ merken (kein Neustart im Takt), Stopp beendet alle, Abgleich wird über den Job angestoßen."""
from __future__ import annotations

import threading
import time

import pytest


@pytest.fixture
def mgr(monkeypatch):
    from backend import idle_manager
    started, stops = [], {}

    def fake_watch(acc, stop, trigger, **kw):
        started.append(acc["id"])
        stops[acc["id"]] = stop
        if acc.get("unsupported"):
            return "unsupported"
        stop.wait()
        return "stopped"
    monkeypatch.setattr(idle_manager.idle, "watch", fake_watch)
    m = idle_manager.Manager()
    yield m, started, stops
    m.stop_all()


def _accs(*ids, **extra):
    return [{"id": i, "address": f"{i}@x.de", "username": i, **extra} for i in ids]


def _until(cond, timeout=3.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if cond():
            return True
        time.sleep(0.01)
    return False


def test_je_konto_genau_ein_thread(mgr):
    m, started, _ = mgr
    m.reconcile(_accs("a", "b"))
    m.reconcile(_accs("a", "b"))
    assert _until(lambda: sorted(started) == ["a", "b"])
    time.sleep(0.1)
    assert sorted(started) == ["a", "b"] and sorted(m.running()) == ["a", "b"]


def test_geloeschtes_konto_wird_beendet(mgr):
    m, started, stops = mgr
    m.reconcile(_accs("a", "b"))
    assert _until(lambda: len(started) == 2)
    m.reconcile(_accs("a"))
    assert stops["b"].is_set() and not stops["a"].is_set()
    assert _until(lambda: m.running() == ["a"])


def test_unsupported_nicht_neu_starten(mgr):
    m, started, _ = mgr
    m.reconcile(_accs("a", unsupported=True))
    assert _until(lambda: m.running() == [])
    m.reconcile(_accs("a", unsupported=True))
    time.sleep(0.1)
    assert started == ["a"]


def test_geaenderte_zugangsdaten_neu_starten(mgr):
    """Konto geändert (anderer Server/Benutzer) → alter Thread weg, neuer mit neuen Daten; auch nach „unsupported“."""
    m, started, stops = mgr
    m.reconcile(_accs("a"))
    assert _until(lambda: started == ["a"])
    first = stops["a"]
    m.reconcile([{"id": "a", "address": "a@x.de", "username": "neu", "imap_host": "anders"}])
    assert first.is_set() and _until(lambda: started == ["a", "a"])


def test_stop_all(mgr):
    m, started, stops = mgr
    m.reconcile(_accs("a", "b"))
    assert _until(lambda: len(started) == 2)
    m.stop_all()
    assert all(s.is_set() for s in stops.values()) and _until(lambda: m.running() == [])


def test_ausgeschaltet_per_einstellung(mgr, monkeypatch):
    m, started, _ = mgr
    monkeypatch.setenv("HH_MAILBOX_IDLE", "0")
    m.reconcile(_accs("a"))
    time.sleep(0.1)
    assert started == [] and m.running() == []


def test_ausloeser_startet_abgleich_im_hauptloop(monkeypatch):
    """Der IDLE-Thread stößt den Abgleich im Event-Loop an (sync_job._run ist async + sperrt je Konto)."""
    import asyncio

    from backend import idle_manager, sync_job
    ran = []

    async def fake_run(acc):
        ran.append(acc["id"])
        return True
    monkeypatch.setattr(sync_job, "_run", fake_run)

    async def main():
        loop = asyncio.get_running_loop()
        trig = idle_manager._trigger(loop)
        t = threading.Thread(target=trig, args=({"id": "a"},))
        t.start()
        t.join()
        for _ in range(50):
            if ran:
                break
            await asyncio.sleep(0.01)
    asyncio.run(main())
    assert ran == ["a"]


def test_job_nutzt_alle_konten(monkeypatch):
    import asyncio

    from backend import accounts, idle_manager
    seen = []
    monkeypatch.setattr(accounts, "all_accounts", lambda: _accs("x", "y"))
    monkeypatch.setattr(idle_manager.MANAGER, "reconcile", lambda accs, trig: seen.append([a["id"] for a in accs]))
    asyncio.run(idle_manager.job())
    assert seen == [["x", "y"]]

