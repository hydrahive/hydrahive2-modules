"""Dienst-Teil „Dashboard“: Entscheidung Video/Dashboard je Durchlauf und die Dashboard-Schleife (EVDI-Bilder → Display).

Aus main.py ausgelagert, damit die Datei klein bleibt. `runner` ist der laufende `main.Runner`.
"""
from __future__ import annotations

import logging
import os
import time

from . import mode

FPS = 20
log = logging.getLogger("vitrine.dashboard")


def from_env():
    """Dashboard nur, wenn der Installer den Kiosk eingerichtet hat (VITRINE_KIOSK_DISPLAY + VITRINE_KIOSK_XAUTH)."""
    disp, xauth = os.environ.get("VITRINE_KIOSK_DISPLAY"), os.environ.get("VITRINE_KIOSK_XAUTH")
    if not disp:
        return None
    if xauth:
        os.environ["XAUTHORITY"] = xauth
    from .dashboard import Dashboard
    from .idle import Idle
    log.info("Dashboard aktiv (X %s)", disp)
    return Dashboard(w=1080, h=1920, idle=Idle(disp), pointer=Idle(disp), fps=FPS).start()


def wants(runner) -> bool:
    """True, wenn jetzt das Dashboard gezeigt werden soll. Pflegt state[mode/dashboard]."""
    dash = runner._dash
    if dash is None:
        runner.state.update(mode="video", dashboard="aus")
        return False
    avail = dash.available()
    m = runner._mode.update(idle_ms=dash.idle_ms() if avail else None, available=avail, now=time.monotonic(),
                            back_requested=mode.take_back_request(runner.data),
                            chat_busy=mode.chat_busy(runner.data, now=time.time()))
    runner.state.update(mode=m, dashboard="bereit" if avail else f"nicht verfügbar: {dash.reason or '?'}")
    return m == "dashboard"


def due(runner) -> bool:
    """Gedrosselt prüfen (alle `runner.mode_every` s) – der Videoweg ruft das jedes Bild auf."""
    t = time.monotonic()
    if t - runner._mode_t < runner.mode_every:
        return False
    runner._mode_t = t
    return True


def play(runner, disp, max_frames) -> None:
    """Dashboard zeigen, bis zurück zum Video geschaltet wird. Ohne neues Bild alle `dashboard_repeat` s das letzte erneut."""
    dash = runner._dash
    dash.set_active(True)
    runner._write_state()
    last_sent, period = -1e18, 1.0 / FPS
    try:
        while max_frames is None or runner.state["frames"] < max_frames:
            t0 = time.monotonic()
            jpeg = dash.take_frame()
            if jpeg is None and dash.last_jpeg is not None and t0 - last_sent >= runner.dashboard_repeat:
                jpeg = dash.last_jpeg                 # Display braucht regelmäßig Bilder, sonst zeigt es eigene Inhalte
            if jpeg is not None:
                runner._send_jpeg(disp, jpeg)
                last_sent = t0
            if due(runner) and not wants(runner):
                runner._write_state()
                return
            rest = period - (time.monotonic() - t0)
            if rest > 0:
                runner.sleep(rest)
        runner._write_state()
    finally:
        dash.set_active(False)


def night_loop(runner, disp, prog, key, max_frames, frame_fn) -> bool:
    """Nachtbild (1 Bild/s). True = Programm oder Modus hat gewechselt. Mit Dashboard alle ¼ s nach der Maus sehen."""
    while max_frames is None or runner.state["frames"] < max_frames:
        now = runner.now()
        runner._send(disp, frame_fn(prog.night, disp.width, disp.height, now))
        if runner._program(now).key() != key or (due(runner) and wants(runner)):
            return True
        runner.sleep(1.0 if runner._dash is None else 0.25)
    runner._write_state()
    return False
