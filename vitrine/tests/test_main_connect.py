"""Display nach dem Start erwischen: Ohne Host meldet es sich nur 1–2 s am USB an (gemessen 16.10.2026 auf .226).

Der Dienst muss in dieser Zeit verbinden, sonst fällt das Display in seine eigene Anzeige zurück und bleibt dort.
"""
from __future__ import annotations

import json

from renderer import main
from test_main import FakeDisplay, FakeFrames


class Uhr:
    """Simulierte Zeit: sleep() lässt sie vorrücken."""

    def __init__(self):
        self.t = 0.0

    def sleep(self, s):
        self.t += s


def _runner(tmp_path, connect, uhr):
    return main.Runner(data_dir=tmp_path, connect=connect, frames=lambda *a: FakeFrames(1080, 1920),
                       status=lambda: "", sleep=uhr.sleep, fps=30)


def test_kurzes_fenster_wird_erwischt(tmp_path):
    """Display taucht bei t=10,3 s für 1 s auf – der Dienst muss es in diesem Fenster öffnen."""
    uhr = Uhr()
    versuche = []

    def connect():
        versuche.append(uhr.t)
        return FakeDisplay() if 10.3 <= uhr.t < 11.3 else None

    r = _runner(tmp_path, connect, uhr)
    r.run(max_frames=1, max_waits=200)
    assert r.state["frames"] == 1, f"Fenster verpasst; Versuche bei {versuche[-8:]}"


def test_suchintervall_kurz_genug(tmp_path):
    """Kein einzelnes Warten darf länger sein als das kürzeste beobachtete Fenster (1 s) – mit Reserve."""
    assert main.SEARCH_SECONDS <= 0.25


def test_nach_verlust_sofort_wieder_suchen(tmp_path):
    uhr = Uhr()
    displays = [FakeDisplay(fail_after=2), None, None, FakeDisplay()]

    def connect():
        return displays.pop(0) if displays else None

    r = _runner(tmp_path, connect, uhr)
    r.run(max_frames=4, max_waits=20)
    assert r.state["frames"] == 4 and r.state["reconnects"] == 1
    assert uhr.t <= 1.0, f"nach dem Verlust zu lange gewartet: {uhr.t:.2f} s"


def test_suchen_schreibt_status_nicht_bei_jedem_versuch(tmp_path, monkeypatch):
    """Bei 5 Versuchen pro Sekunde nicht jedes Mal state.json schreiben – höchstens etwa einmal pro Sekunde."""
    uhr = Uhr()
    writes = []
    r = _runner(tmp_path, lambda: None, uhr)
    orig = r._write_state
    monkeypatch.setattr(r, "_write_state", lambda: (writes.append(uhr.t), orig()))
    r.run(max_frames=1, max_waits=50)                      # 50 Versuche ≈ 10 s
    assert 1 <= len(writes) <= 15, f"{len(writes)} Schreibvorgänge"
    assert json.loads((tmp_path / "state.json").read_text())["connected"] is False
