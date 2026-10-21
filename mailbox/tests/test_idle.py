"""M2 Schritt 9: IMAP IDLE (RFC 2177) gegen einen echten TCP-Server mit dem echten imaplib.

Neue Mail → Abgleich angestoßen; kein IDLE beim Server → aufgeben (5-Minuten-Takt bleibt); Abbruch → neu verbinden
mit Wartezeit; Stopp → sauber beenden (DONE); IDLE spätestens nach max_idle erneuern; Posteingang nur lesend.
"""
from __future__ import annotations

import imaplib
import threading
import time

import pytest
from _fake_idle import IdleServer

ACC = {"id": "acc1", "address": "till@example.net", "username": "till@example.net"}


@pytest.fixture
def srv():
    s = IdleServer()
    yield s
    s.close()


def _watch(srv, *, stop, calls, **kw):
    from backend import idle
    kw = {"poll": 0.05, "backoff": (0.05,), "debounce": 0.0, **kw}
    t_res = {}

    def run():
        t_res["r"] = idle.watch(ACC, stop, lambda acc: calls.append(time.monotonic()),
                                open_conn=lambda acc: imaplib.IMAP4("127.0.0.1", srv.port),
                                password_of=lambda aid: "pw", **kw)
    t = threading.Thread(target=run, daemon=True)
    t.start()
    return t, t_res


def _until(cond, timeout=5.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if cond():
            return True
        time.sleep(0.02)
    return False


def test_neue_mail_stoesst_abgleich_an(srv):
    stop, calls = threading.Event(), []
    t, _ = _watch(srv, stop=stop, calls=calls)
    assert srv.wait_idle()
    t0 = time.monotonic()
    srv.push(b"* 4 EXISTS")
    assert _until(lambda: calls), "Abgleich nicht angestoßen"
    assert calls[0] - t0 < 2.0
    assert srv.selects and set(srv.selects) == {"EXAMINE"}, "Posteingang nur lesend öffnen"
    stop.set()
    t.join(5)
    assert not t.is_alive()


def test_expunge_stoesst_an_fetch_nicht(srv):
    stop, calls = threading.Event(), []
    t, _ = _watch(srv, stop=stop, calls=calls)
    assert srv.wait_idle()
    srv.push(b"* 2 FETCH (FLAGS (\\Seen))")
    time.sleep(0.4)
    assert calls == []
    srv.push(b"* 2 EXPUNGE")
    assert _until(lambda: calls)
    stop.set()
    t.join(5)


def test_server_ohne_idle_gibt_auf(srv):
    srv.idle = False
    stop, calls = threading.Event(), []
    t, res = _watch(srv, stop=stop, calls=calls)
    t.join(5)
    assert not t.is_alive() and res["r"] == "unsupported" and calls == [] and srv.idles == 0


def test_idle_abgelehnt_gibt_auf(srv):
    """Server nennt IDLE, lehnt es aber ab (BAD/NO) → aufgeben statt endlos neu versuchen."""
    srv.idle_reply = b"X BAD nope"           # Tag egal: keine Fortsetzung „+“
    stop, calls = threading.Event(), []
    t, res = _watch(srv, stop=stop, calls=calls, start_timeout=0.5)
    t.join(5)
    assert not t.is_alive() and res["r"] == "unsupported"


def test_abbruch_neu_verbinden(srv):
    stop, calls = threading.Event(), []
    t, _ = _watch(srv, stop=stop, calls=calls)
    assert srv.wait_idle()
    srv.drop()
    assert _until(lambda: srv.logins >= 2), "nach Abbruch neu verbunden"
    assert srv.wait_idle()
    srv.push(b"* 9 EXISTS")
    assert _until(lambda: calls)
    stop.set()
    t.join(5)


def test_falsches_passwort_wartet_lange(srv):
    """Anmeldung abgelehnt: nicht im Sekundentakt neu versuchen (Konto-Sperre beim Anbieter)."""
    srv.password = "anders"
    stop, calls = threading.Event(), []
    t, res = _watch(srv, stop=stop, calls=calls, backoff=(0.05,), auth_backoff=10.0)
    time.sleep(0.6)
    assert srv.logins == 1
    stop.set()
    t.join(5)
    assert not t.is_alive()


def test_stopp_beendet_sauber(srv):
    stop, calls = threading.Event(), []
    t, res = _watch(srv, stop=stop, calls=calls)
    assert srv.wait_idle()
    t0 = time.monotonic()
    stop.set()
    t.join(5)
    assert not t.is_alive() and time.monotonic() - t0 < 2.0 and res["r"] == "stopped"
    assert srv.dones == 1, "IDLE mit DONE beendet"


def test_idle_wird_erneuert(srv):
    stop, calls = threading.Event(), []
    t, _ = _watch(srv, stop=stop, calls=calls, max_idle=0.3)
    assert _until(lambda: srv.idles >= 3)
    assert srv.dones >= 2 and srv.logins == 1, "erneuern ohne neue Anmeldung"
    stop.set()
    t.join(5)


def test_entprellen(srv):
    """Viele Meldungen kurz hintereinander → höchstens ein Abgleich je Zeitfenster."""
    stop, calls = threading.Event(), []
    t, _ = _watch(srv, stop=stop, calls=calls, debounce=1.0)
    assert srv.wait_idle()
    srv.push(b"* 4 EXISTS")
    assert _until(lambda: len(calls) == 1)
    assert srv.wait_idle()
    for n in range(5, 9):
        srv.push(f"* {n} EXISTS".encode())
        time.sleep(0.05)
    time.sleep(0.5)
    assert len(calls) == 1, "im Zeitfenster kein zweiter Abgleich"
    assert _until(lambda: len(calls) == 2, timeout=3.0), "danach doch noch einer (nichts verloren)"
    assert calls[1] - calls[0] >= 0.95
    stop.set()
    t.join(5)


def test_abgleich_fehler_stoppt_nicht(srv):
    from backend import idle
    stop, n = threading.Event(), []

    def boom(acc):
        n.append(1)
        raise RuntimeError("Abgleich kaputt")
    t = threading.Thread(target=lambda: idle.watch(ACC, stop, boom, open_conn=lambda a: imaplib.IMAP4("127.0.0.1", srv.port),
                                                   password_of=lambda a: "pw", poll=0.05, backoff=(0.05,), debounce=0.0),
                         daemon=True)
    t.start()
    assert srv.wait_idle()
    srv.push(b"* 4 EXISTS")
    assert _until(lambda: n)
    assert srv.wait_idle(), "nach dem Fehler weiter im IDLE"
    srv.push(b"* 5 EXISTS")
    assert _until(lambda: len(n) == 2)
    stop.set()
    t.join(5)

