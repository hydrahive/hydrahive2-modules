"""Dashboard-Thread: arbeitet EVDI-Ereignisse immer ab (sonst hängt xrandr), Bilder nur wenn aktiv, Fehler → Grund."""
from __future__ import annotations

import time

from renderer import dashboard
from renderer.evdi_source import EvdiUnavailable


class FakeSrc:
    def __init__(self, fail_after=None):
        self.polls, self.grabs, self.ready, self.closed, self.fail_after = 0, 0, True, False, fail_after

    def poll_events(self):
        self.polls += 1

    def next_jpeg(self, cursor=None):
        self.grabs += 1
        if self.fail_after is not None and self.grabs > self.fail_after:
            raise OSError("evdi weg")
        return b"\xff\xd8" + bytes([self.grabs % 250]) + b"\xff\xd9"

    def close(self):
        self.closed = True


class Idle:
    def idle_ms(self):
        return 42


def _wait(cond, t=2.0):
    end = time.monotonic() + t
    while time.monotonic() < end:
        if cond():                                  # Ergebnis nur einmal holen (take_frame verbraucht das Bild)
            return True
        time.sleep(0.01)
    return False


def _dash(src, **kw):
    return dashboard.Dashboard(w=1080, h=1920, idle=Idle(), open_source=lambda w, h: src, fps=200, tick=0.005, **kw).start()


def test_inaktiv_nur_ereignisse_keine_bilder():
    src = FakeSrc()
    d = _dash(src)
    try:
        assert _wait(lambda: src.polls >= 5)
        assert src.grabs == 0 and d.take_frame() is None
        assert _wait(d.available) and d.idle_ms() == 42
    finally:
        d.close()
    assert src.closed


def test_aktiv_liefert_bilder():
    src = FakeSrc()
    d = _dash(src)
    try:
        d.set_active(True)
        assert _wait(lambda: d.take_frame() is not None)
        assert d.last_jpeg[:2] == b"\xff\xd8"
    finally:
        d.close()


def test_fehler_schliesst_quelle_und_nennt_grund():
    src = FakeSrc(fail_after=1)
    d = _dash(src, retry_open=999)
    try:
        d.set_active(True)
        assert _wait(lambda: d.reason is not None and "evdi weg" in d.reason)
        assert src.closed and not d.available()
    finally:
        d.close()


def test_evdi_nicht_da_grund_und_kein_absturz():
    def kaputt(w, h):
        raise EvdiUnavailable("libevdi fehlt: x")
    d = dashboard.Dashboard(w=1080, h=1920, idle=Idle(), open_source=kaputt, tick=0.005).start()
    try:
        assert _wait(lambda: d.reason == "libevdi fehlt: x")
        assert not d.available()
    finally:
        d.close()


def test_nicht_verfuegbar_solange_kiosk_den_bildschirm_nicht_eingeschaltet_hat():
    """EVDI offen, aber noch kein Modus vom X-Server → Dashboard nicht anbieten (sonst schwarzes Bild statt Video)."""
    src = FakeSrc()
    src.ready = False
    d = _dash(src)
    try:
        assert _wait(lambda: src.polls >= 3)
        assert not d.available() and "Kiosk" in (d.reason or "")
        src.ready = True
        assert _wait(d.available)
    finally:
        d.close()
