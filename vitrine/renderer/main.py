"""Vitrine-Dienst: Programm (Kalender/Nacht) → Video + Overlay → Display. Verbindet sich selbst neu.

Start: python -m renderer.main  (Umgebung: VITRINE_DATA = Modul-Datenverzeichnis)
Für das Backend: <data>/state.json (Status) und <data>/preview.jpg (Vorschau, 270×480).
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import os
import time
from pathlib import Path
from typing import Callable, Iterable

import usb.core
from PIL import Image

from . import aic, cached_play, cards, config, hydra_state, inbox, mode, night, preview, program, scene, sysinfo, video, warmer
from . import play_dashboard as dash_play
from .frames import _connect_real, encode, fallback_frame, write_preview  # noqa: F401 - auch von Tests genutzt

SEARCH_SECONDS = 0.2      # ohne Host meldet sich das Display nur 1–2 s am USB an (gemessen 16.10.) – oft genug nachsehen
RETRY_SECONDS = SEARCH_SECONDS
STATE_EVERY = 1.0         # beim Suchen state.json höchstens etwa einmal pro Sekunde schreiben
STATUS_EVERY = 5.0
DEFAULT_FPS = 24          # Atelier-Videos haben 24 fps; mehr kostet nur CPU
log = logging.getLogger("vitrine")


class _Switch(Exception):
    """Programm hat sich geändert → Bildquelle neu aufbauen."""


class Runner:
    def __init__(self, *, data_dir: Path, connect: Callable = _connect_real,
                 frames: Callable[..., Iterable[Image.Image]] | None = None,
                 status: Callable[[], str] = sysinfo.current, sleep: Callable[[float], None] = time.sleep,
                 fps: int = DEFAULT_FPS, quality: int = 80,
                 program: Callable[[dt.datetime], program.Program] | None = None,
                 now: Callable[[], dt.datetime] = dt.datetime.now, check_every: float = 1.0, warmer=None, dashboard=None):
        self.data = data_dir
        self.connect, self.status, self.sleep, self.now = connect, status, sleep, now
        self.fps, self.quality, self.check_every = fps, quality, check_every
        self._frames = frames or self._video_frames
        self._watch, self._config = config.Watcher(data_dir), config.load(data_dir)
        self._program = program or self._program_from_config
        self._uses_config = program is None          # Bildrate aus config.json (Cockpit); sonst fester Wert (Tests)
        self.preview_every, self._preview_t, self.inbox_every, self.cache_check_every = 10.0, 0.0, 1.0, 2.0
        self._warmer = warmer
        self._dash, self._mode = dashboard, mode.Mode(return_after=mode.return_seconds(self._config))
        self.mode_every, self._mode_t, self.dashboard_repeat = 0.25 if dashboard else 1e9, -1e18, 2.0
        self.state = {"connected": False, "frames": 0, "reconnects": 0, "size": None, "video": None, "rule": None,
                      "holiday": None, "night": None, "error": None, "cache": None, "preview": None, "mode": "video",
                      "dashboard": "aus" if dashboard is None else "startet"}

    def _program_from_config(self, now: dt.datetime) -> program.Program:
        fresh = self._watch.poll()
        if fresh is not None:
            self._config = fresh
            self._mode.return_after = mode.return_seconds(fresh)
        return preview.current(self.data, self._config, now)

    def source(self) -> Path | None:
        return program.current(self.data, self._config, self.now()).video

    def _video_frames(self, src, w, h, fps):
        if src is None or not Path(src).exists():
            img = fallback_frame(w, h)
            while True:
                yield img
        prepared = video.prepare(Path(src), self.data / "cache", w, h, fps)
        while True:
            yield from video.frames(prepared, w, h, fps)

    def _write_state(self) -> None:
        if self._warmer is not None:
            self.state["cache"] = self._warmer.status()
        tmp = self.data / "state.json.tmp"
        tmp.write_text(json.dumps({**self.state, "updated": time.time()}))
        tmp.replace(self.data / "state.json")

    def _send(self, disp, img: Image.Image) -> None:
        self._send_jpeg(disp, encode(img, self.quality), img)

    def _send_jpeg(self, disp, jpeg: bytes, img: Image.Image | None = None) -> None:
        disp.send_jpeg(jpeg)
        self.state["frames"] += 1
        t = time.monotonic()
        if t - self._preview_t >= self.preview_every:
            self._preview_t = t
            write_preview(self.data, jpeg, img)

    def run(self, *, max_frames: int | None = None, max_waits: int | None = None) -> None:
        self.data.mkdir(parents=True, exist_ok=True)
        waits = 0
        while max_frames is None or self.state["frames"] < max_frames:
            try:
                disp = self.connect()
            except (usb.core.USBError, aic.DisplayError) as e:
                # direkt nach dem Wiederanstecken meldet libusb kurz „Entity not found“ – einfach erneut versuchen
                log.info("Display noch nicht bereit: %s", e)
                self.state.update(error=str(e))
                disp = None
            if disp is None:
                self.state.update(connected=False)
                if waits % max(1, round(STATE_EVERY / SEARCH_SECONDS)) == 0:
                    self._write_state()
                waits += 1
                if max_waits is not None and waits > max_waits:
                    return
                self.sleep(RETRY_SECONDS)
                continue
            self.state.update(connected=True, size=[disp.width, disp.height], error=None)
            try:
                while max_frames is None or self.state["frames"] < max_frames:
                    try:
                        self._play(disp, max_frames)
                    except _Switch:
                        continue
            except (usb.core.USBError, aic.DisplayError) as e:
                log.warning("Display-Verbindung verloren: %s", e)
                self.state.update(connected=False, error=str(e))
                self.state["reconnects"] += 1
                self._write_state()
            finally:
                disp.close()

    def _play(self, disp, max_frames) -> None:
        w, h = disp.width, disp.height
        if self._dash is not None and dash_play.wants(self):
            return dash_play.play(self, disp, max_frames)
        prog = self._program(self.now())
        key = prog.key()
        self.state.update(video=prog.video.name if prog.video else None, rule=prog.rule,
                          holiday=prog.holiday, night=prog.night, preview=prog.preview)
        self._write_state()
        if prog.night:
            return self._play_night(disp, prog, key, max_frames)
        overlay, card_layer = scene.Overlay(w, h), cards.Cards(w, h)
        st, alert = self._status_line()
        fps = prog.fps if self._uses_config else self.fps
        st_t, chk_t, in_t, period = time.monotonic(), time.monotonic(), -1e9, 1.0 / fps
        msgs: list[dict] = []
        src = cached_play.Source(prog.video, w, h, fps, self.quality, frames=self._frames,
                                 warmer=self._warmer, check_every=self.cache_check_every)
        try:
            while True:
                t0 = time.monotonic()
                if t0 - st_t >= STATUS_EVERY:
                    (st, alert), st_t = self._status_line(), t0
                    self._write_state()
                if t0 - in_t >= self.inbox_every:
                    msgs, in_t = inbox.visible(self.data), t0
                layers = [overlay.render(time.localtime(), st, preview.headline(prog), alert)]
                if msgs:
                    layers.append(card_layer.render(msgs, time.time(), hint=self.state.get("dashboard") == "bereit"))
                try:
                    jpeg = src.next(layers)
                except StopIteration:
                    return
                if src.broken and self.state.get("error") != src.broken:
                    self.state["error"] = src.broken
                    self._write_state()
                self._send_jpeg(disp, jpeg, src.last_frame)
                if max_frames is not None and self.state["frames"] >= max_frames:
                    self._write_state()
                    return
                if t0 - chk_t >= self.check_every:
                    chk_t = t0
                    if self._program(self.now()).key() != key:
                        raise _Switch
                if dash_play.due(self) and dash_play.wants(self):
                    raise _Switch
                dt_ = time.monotonic() - t0
                if dt_ < period:
                    self.sleep(period - dt_)
        finally:
            src.close()

    def _status_line(self) -> tuple[str, bool]:
        return hydra_state.line(self.status(), self.data)

    def _play_night(self, disp, prog, key, max_frames) -> None:
        if dash_play.night_loop(self, disp, prog, key, max_frames, night.frame):
            raise _Switch


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    data = Path(os.environ.get("VITRINE_DATA", "/var/lib/hydrahive2/vitrine"))
    warm = warmer.Warmer(data / "cache", frames=lambda src, w, h, fps: video.frames(
        video.prepare(Path(src), data / "cache", w, h, fps), w, h, fps, loop=False))
    Runner(data_dir=data, quality=int(os.environ.get("VITRINE_QUALITY", "80")), warmer=warm,
           dashboard=dash_play.from_env()).run()


if __name__ == "__main__":
    main()
