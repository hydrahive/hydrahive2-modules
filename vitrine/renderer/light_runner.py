"""S8 Licht-Thread im Vitrine-Dienst (SPEC-LICHT.md). Fehler hier stoppen das Display nie (wie Bluetooth, S7).

Alle TICK_SECONDS: Zustand wählen; nur bei Änderung setzen (ein OpenRGB-Aufruf dauert ~1,2 s), dazu alle REFRESH_SECONDS
neu (falls das Board nach Standby/Neustart in sein Werks-Wabern zurückfällt). Stand für das Cockpit in <daten>/light.json.
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import shutil
import threading
import time
from pathlib import Path

from . import config, light_calendar, light_preview, light_rgb, light_state

TICK_SECONDS, REFRESH_SECONDS, SEARCH_SECONDS, RETRY_SECONDS = 2.0, 600.0, 300.0, 30.0
log = logging.getLogger("vitrine.light")


def _preview_look(light: dict, state: str) -> light_state.Look:
    b = light["brightness"]
    if state == "night":
        return light_state.Look("night", "off", "000000", 0)
    if state in light["states"]:
        return light_state._state_look(light, state)
    if state in light["seasons"]:
        s = light["seasons"][state]
        return light_state.Look(state, s["effect"], s["color"], b)
    return light_state.Look("rest", light["rest_effect"], light["rest_color"], b)   # auch „Anlass“ ohne aktive Regel


class LightRunner:
    def __init__(self, data: Path, *, find=None, apply=None, now=dt.datetime.now):
        self.data, self.cfg_dir, self.now = data, data / "openrgb", now
        self._find = find or (lambda d: light_rgb.find(d))
        self._apply = apply or (lambda look, dev, d: light_rgb.apply(look, dev, d))
        self._watch, self._config = config.Watcher(data), config.load(data)
        self.mem, self.device = light_state.Memory(), None
        self._last_key, self._set_t, self._search_t, self._fail_t = None, -1e18, -1e18, -1e18
        self.status = {"device": None, "state": None, "color": None, "effect": None, "label": "", "preview": None,
                       "error": None}

    def _write(self, t: float) -> None:
        tmp = self.data / "light.json.tmp"
        tmp.write_text(json.dumps({**self.status, "updated": t}))
        tmp.replace(self.data / "light.json")

    def _choose(self, now: dt.datetime) -> light_state.Look | None:
        light = self._config["light"]
        pv = light_preview.active(self.data, t=now.timestamp())
        self.status["preview"] = pv
        if pv is not None and light.get("enabled"):
            if pv == "occasion":
                occ = light_calendar.occasion(self._config, now)
                if occ:
                    return light_state.Look("occasion", occ[1], occ[2], light["brightness"], label=occ[0])
            return _preview_look(light, pv)
        return light_state.choose(self.data, self._config, now, self.mem)

    def tick(self) -> None:
        now = self.now()
        t = now.timestamp()
        fresh = self._watch.poll()
        if fresh is not None:
            self._config = fresh
        look = self._choose(now)
        if look is None:
            self.status.update(state="disabled", color=None, effect=None, label="", error=None)
            self._last_key = None
            return self._write(t)
        if self.device is None:
            if t - self._search_t < SEARCH_SECONDS:
                return
            self._search_t = t
            self.device = self._find(self.cfg_dir)
            if self.device is None:
                self.status.update(device=None, error="Beleuchtung nicht gefunden (OpenRGB, Recht auf das Gerät?)")
                return self._write(t)
            self.status["device"] = self.device.name
        due = look.key() != self._last_key or t - self._set_t >= REFRESH_SECONDS
        if self.status["error"] and look.key() == self._last_key:
            due = due and t - self._fail_t >= RETRY_SECONDS
        if not due:
            return
        try:
            self._apply(look, self.device, self.cfg_dir)
        except light_rgb.LightError as e:
            self._fail_t, self._last_key = t, look.key()
            self.status["error"] = str(e)[:200]
            log.warning("Licht nicht gesetzt: %s", e)
            return self._write(t)
        self._last_key, self._set_t = look.key(), t
        self.status.update(state=look.state, color=look.color, effect=look.effect, label=look.label, error=None)
        self._write(t)

    def loop(self, *, max_ticks: int | None = None, sleep=time.sleep, stop: threading.Event | None = None) -> None:
        n = 0
        while (max_ticks is None or n < max_ticks) and not (stop and stop.is_set()):
            n += 1
            try:
                self.tick()
            except Exception:                              # noqa: BLE001 - Display darf nie mitsterben
                log.exception("Licht-Durchlauf abgebrochen")
            sleep(TICK_SECONDS)


def start(data: Path) -> threading.Event | None:
    """Startet den Licht-Thread (Daemon). None, wenn OpenRGB nicht installiert ist."""
    if shutil.which("openrgb") is None:
        log.info("OpenRGB fehlt – Licht aus")
        return None
    stop = threading.Event()
    runner = LightRunner(data)
    threading.Thread(target=lambda: runner.loop(stop=stop), name="vitrine-light", daemon=True).start()
    return stop
