"""Dashboard-Thread: arbeitet EVDI-Ereignisse immer ab (sonst hängt xrandr), Bilder nur wenn aktiv, Fehler → Grund."""
from __future__ import annotations

import time

from renderer import dashboard
from renderer.evdi_source import EvdiUnavailable


class FakeSrc:
    def __init__(self, fail_after=None):
        self.polls, self.grabs, self.drains, self.ready, self.closed, self.fail_after = 0, 0, 0, True, False, fail_after

    def poll_events(self):
        self.polls += 1

    def drain(self):
        self.drains += 1

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
        assert _wait(lambda: src.drains >= 5)
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
        assert _wait(lambda: src.drains >= 3)
        assert not d.available() and "Kiosk" in (d.reason or "")
        src.ready = True
        assert _wait(d.available)
    finally:
        d.close()


def test_holt_auch_im_videomodus_bilder_ab():
    """Ohne Abholen wartet Xorg bei jedem Bildwechsel bis zum Timeout (flip_done, 10 s) – gemessen am 19.10.2026 auf .2:
    0/s → Xorg 40/40 Proben blockiert; 20/s → 1/40, CPU 0,9 %. Im Video-Modus wird abgeholt, aber kein JPEG gebaut."""
    src = FakeSrc()
    d = _dash(src)
    try:
        assert _wait(lambda: src.drains >= 5)
        assert src.grabs == 0, "kein JPEG im Hintergrund"
    finally:
        d.close()


class StuckX:
    """Nachbau des Hängers vom 19.10.2026 13:44 auf .2: Xorg steckt im EVDI-Bildwechsel (drm_crtc_commit_wait) und
    antwortet auf XQueryPointer erst, wenn der EVDI-Thread weiter Bilder abholt. Fragt der EVDI-Thread selbst nach dem
    Zeiger, warten beide aufeinander."""

    def __init__(self, src, need=5):
        self.src, self.need = src, need
        self.calls = 0

    def pointer(self):
        self.calls += 1
        start = self.src.grabs + self.src.drains
        end = time.monotonic() + 3.0
        while self.src.grabs + self.src.drains < start + self.need:     # X wartet auf weitere Abholungen
            if time.monotonic() > end:
                raise TimeoutError("X hängt – EVDI hat nicht weiter abgeholt")
            time.sleep(0.002)
        return (100 + self.calls, 200)


def test_zeigerabfrage_blockiert_nie_das_bildabholen():
    src = FakeSrc()
    ptr = StuckX(src)
    d = _dash(src, pointer=ptr)
    try:
        d.set_active(True)
        assert _wait(lambda: ptr.calls >= 3, t=4.0), "Zeiger wird abgefragt"
        before = src.grabs
        assert _wait(lambda: src.grabs >= before + 20, t=2.0), "EVDI holt weiter ab, auch während X auf ihn wartet"
        assert d.reason is None
    finally:
        d.close()


def test_zeiger_kommt_ins_bild():
    src = FakeSrc()
    seen = []
    orig = src.next_jpeg

    def next_jpeg(cursor=None):
        seen.append(cursor)
        return orig(cursor=cursor)
    src.next_jpeg = next_jpeg

    class Ptr:
        def pointer(self):
            return (321, 654)
    d = _dash(src, pointer=Ptr())
    try:
        d.set_active(True)
        assert _wait(lambda: (321, 654) in seen)
    finally:
        d.close()


def test_ohne_dashboard_wird_der_zeiger_nicht_abgefragt():
    src = FakeSrc()

    class Ptr:
        calls = 0

        def pointer(self):
            Ptr.calls += 1
            return (1, 1)
    d = _dash(src, pointer=Ptr())
    try:
        assert _wait(lambda: src.drains >= 10)
        assert Ptr.calls == 0, "im Videomodus keine X-Abfragen für den Zeiger"
    finally:
        d.close()
