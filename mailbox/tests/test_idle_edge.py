"""M2 Schritt 9 (Teil 3): IDLE-Grenzfälle – Lesepuffer (Python 3.12), keine Socket-Timeouts, Wartezeit bei Ausfall."""
from __future__ import annotations

import threading
import time

from test_idle import ACC, _until, _watch, srv  # noqa: F401 - Fixture


def test_zwei_meldungen_in_einem_paket(srv):  # noqa: F811
    """Zwei Zeilen in EINEM TCP-Paket: die zweite liegt danach im Lesepuffer, den select() nicht sieht. Sie muss
    trotzdem sofort gelesen werden (nicht erst, wenn irgendwann neue Daten kommen)."""
    stop, calls = threading.Event(), []
    t, _ = _watch(srv, stop=stop, calls=calls, poll=30.0, debounce=0.0)
    assert srv.wait_idle()
    srv.push(b"* 1 RECENT\r\n* 4 EXISTS")
    assert _until(lambda: calls, timeout=2.0), "zweite Zeile im Puffer übersehen"
    stop.set()
    srv.drop()
    t.join(5)


def test_neustart_ohne_socket_timeout(srv):  # noqa: F811
    """Kein Socket-Timeout setzen (3.12: Datei-Hülle danach kaputt) – nach vielen leeren Runden geht Lesen weiter."""
    stop, calls = threading.Event(), []
    t, _ = _watch(srv, stop=stop, calls=calls, poll=0.02)
    assert srv.wait_idle()
    time.sleep(0.5)                                   # ~25 leere Runden
    srv.push(b"* 4 EXISTS")
    assert _until(lambda: calls)
    stop.set()
    t.join(5)


def test_server_weg_wartet_wachsend():
    """Server nicht erreichbar: neue Versuche mit wachsender Wartezeit, kein Dauerfeuer."""
    from backend import idle
    stop, tries = threading.Event(), []

    def refuse(acc):
        tries.append(time.monotonic())
        raise ConnectionRefusedError("refused")
    t = threading.Thread(target=lambda: idle.watch(ACC, stop, lambda a: None, open_conn=refuse,
                                                   password_of=lambda a: "pw", backoff=(0.1, 0.3, 10.0)), daemon=True)
    t.start()
    time.sleep(0.9)
    stop.set()
    t.join(5)
    assert len(tries) == 3, tries
    gaps = [b - a for a, b in zip(tries, tries[1:])]
    assert gaps[0] >= 0.09 and gaps[1] >= 0.29
