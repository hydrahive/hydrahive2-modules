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

from . import aic, cards, config, hydra_state, inbox, night, program, scene, sysinfo, video
from .frames import _connect_real, encode, fallback_frame  # noqa: F401 - auch von Tests genutzt

RETRY_SECONDS = 2.0
STATUS_EVERY = 5.0
DEFAULT_FPS = 24          # Atelier-Videos haben 24 fps; mehr kostet nur CPU
PREVIEW_SIZE = (270, 480)
log = logging.getLogger("vitrine")


class _Switch(Exception):
    """Programm hat sich geändert → Bildquelle neu aufbauen."""


class Runner:
    def __init__(self, *, data_dir: Path, connect: Callable = _connect_real,
                 frames: Callable[..., Iterable[Image.Image]] | None = None,
                 status: Callable[[], str] = sysinfo.current, sleep: Callable[[float], None] = time.sleep,
                 fps: int = DEFAULT_FPS, quality: int = 80,
                 program: Callable[[dt.datetime], program.Program] | None = None,
                 now: Callable[[], dt.datetime] = dt.datetime.now, check_every: float = 1.0):
        self.data = data_dir
        self.connect, self.status, self.sleep, self.now = connect, status, sleep, now
        self.fps, self.quality, self.check_every = fps, quality, check_every
        self._frames = frames or self._video_frames
        self._watch = config.Watcher(data_dir)
        self._config = config.load(data_dir)
        self._program = program or self._program_from_config
        self.preview_every = 10.0
        self._preview_t = 0.0
        self.inbox_every = 1.0
        self.state = {"connected": False, "frames": 0, "reconnects": 0, "size": None, "video": None,
                      "rule": None, "holiday": None, "night": None, "error": None}

    # --- Programm ----------------------------------------------------------------------------------
    def _program_from_config(self, now: dt.datetime) -> program.Program:
        fresh = self._watch.poll()
        if fresh is not None:
            self._config = fresh
        return program.current(self.data, self._config, now)

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

    # --- Ausgabe -----------------------------------------------------------------------------------
    def _write_state(self) -> None:
        tmp = self.data / "state.json.tmp"
        tmp.write_text(json.dumps({**self.state, "updated": time.time()}))
        tmp.replace(self.data / "state.json")

    def _send(self, disp, img: Image.Image) -> None:
        disp.send_jpeg(encode(img, self.quality))
        self.state["frames"] += 1
        t = time.monotonic()
        if t - self._preview_t >= self.preview_every:
            self._preview_t = t
            tmp = self.data / "preview.jpg.tmp"
            img.resize(PREVIEW_SIZE).save(tmp, "JPEG", quality=80)
            tmp.replace(self.data / "preview.jpg")

    # --- Schleifen ---------------------------------------------------------------------------------
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
        prog = self._program(self.now())
        key = prog.key()
        self.state.update(video=prog.video.name if prog.video else None, rule=prog.rule,
                          holiday=prog.holiday, night=prog.night)
        self._write_state()
        if prog.night:
            return self._play_night(disp, prog, key, max_frames)
        overlay, card_layer = scene.Overlay(w, h), cards.Cards(w, h)
        st, alert = self._status_line()
        st_t, chk_t, in_t, period = time.monotonic(), time.monotonic(), -1e9, 1.0 / self.fps
        msgs: list[dict] = []
        for frame in self._frames(prog.video, w, h, self.fps):
            t0 = time.monotonic()
            if t0 - st_t >= STATUS_EVERY:
                (st, alert), st_t = self._status_line(), t0
                self._write_state()
            if t0 - in_t >= self.inbox_every:
                msgs, in_t = inbox.visible(self.data), t0
            img = scene.compose(frame, overlay.render(time.localtime(), st, prog.holiday, alert))
            if msgs:
                img = scene.compose(img, card_layer.render(msgs, time.time()))
            self._send(disp, img)
            if max_frames is not None and self.state["frames"] >= max_frames:
                self._write_state()
                return
            if t0 - chk_t >= self.check_every:
                chk_t = t0
                if self._program(self.now()).key() != key:
                    raise _Switch
            dt_ = time.monotonic() - t0
            if dt_ < period:
                self.sleep(period - dt_)

    def _status_line(self) -> tuple[str, bool]:
        base = self.status()
        more, alert = hydra_state.extra(self.data)
        return (f"{base}  ·  {more}" if more and base else base or more), alert

    def _play_night(self, disp, prog, key, max_frames) -> None:
        while max_frames is None or self.state["frames"] < max_frames:
            now = self.now()
            self._send(disp, night.frame(prog.night, disp.width, disp.height, now))
            if self._program(now).key() != key:
                raise _Switch
            self.sleep(1.0)
        self._write_state()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    data = Path(os.environ.get("VITRINE_DATA", "/var/lib/hydrahive2/vitrine"))
    Runner(data_dir=data, fps=int(os.environ.get("VITRINE_FPS", str(DEFAULT_FPS))),
           quality=int(os.environ.get("VITRINE_QUALITY", "80"))).run()


if __name__ == "__main__":
    main()
