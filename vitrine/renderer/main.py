"""Vitrine-Dienst: Video in Schleife + Overlay → Display. Verbindet sich selbst neu.

Start: python -m renderer.main  (Umgebung: VITRINE_DATA = Modul-Datenverzeichnis)
Status für das Backend: <data>/state.json
"""
from __future__ import annotations

import io
import json
import logging
import os
import time
from pathlib import Path
from typing import Callable, Iterable

import usb.core
from PIL import Image

from . import aic, scene, sysinfo, video

RETRY_SECONDS = 2.0
DEFAULT_FPS = 24          # Atelier-Videos haben 24 fps; mehr kostet nur CPU
STATUS_EVERY = 5.0
log = logging.getLogger("vitrine")


def encode(img: Image.Image, quality: int) -> bytes:
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=quality)
    return buf.getvalue()


def fallback_frame(w: int, h: int) -> Image.Image:
    """Ohne Video: ruhiger dunkler Verlauf (Uhr/Status liegen darüber)."""
    top, bottom = (12, 18, 32), (24, 40, 64)
    grad = Image.linear_gradient("L").resize((w, h))
    return Image.composite(Image.new("RGB", (w, h), bottom), Image.new("RGB", (w, h), top), grad)


def _connect_real():
    dev = aic.find()
    return aic.Display.open(dev) if dev is not None else None


class Runner:
    def __init__(self, *, data_dir: Path, connect: Callable = _connect_real,
                 frames: Callable[..., Iterable[Image.Image]] | None = None,
                 status: Callable[[], str] = sysinfo.current, sleep: Callable[[float], None] = time.sleep,
                 fps: int = DEFAULT_FPS, quality: int = 80):
        self.data = data_dir
        self.connect, self.status, self.sleep = connect, status, sleep
        self.fps, self.quality = fps, quality
        self._frames = frames or self._video_frames
        self.state = {"connected": False, "frames": 0, "reconnects": 0, "size": None, "video": None, "error": None}

    def source(self) -> Path | None:
        return video.pick(self.data / "videos")

    def _video_frames(self, src, w, h, fps):
        if src is None:
            img = fallback_frame(w, h)
            while True:
                yield img
        prepared = video.prepare(src, self.data / "cache", w, h, fps)
        while True:
            yield from video.frames(prepared, w, h, fps)

    def _write_state(self) -> None:
        tmp = self.data / "state.json.tmp"
        tmp.write_text(json.dumps({**self.state, "updated": time.time()}))
        tmp.replace(self.data / "state.json")

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
                self._play(disp, max_frames)
            except (usb.core.USBError, aic.DisplayError) as e:
                log.warning("Display-Verbindung verloren: %s", e)
                self.state.update(connected=False, error=str(e))
                self.state["reconnects"] += 1
                self._write_state()
            finally:
                disp.close()

    def _play(self, disp, max_frames) -> None:
        w, h = disp.width, disp.height
        src = self.source()
        self.state["video"] = src.name if src else None
        overlay = scene.Overlay(w, h)
        st, st_t, period = self.status(), time.monotonic(), 1.0 / self.fps
        self._write_state()
        for frame in self._frames(src, w, h, self.fps):
            t0 = time.monotonic()
            if t0 - st_t >= STATUS_EVERY:
                st, st_t = self.status(), t0
                self._write_state()
            disp.send_jpeg(encode(scene.compose(frame, overlay.render(time.localtime(), st)), self.quality))
            self.state["frames"] += 1
            if max_frames is not None and self.state["frames"] >= max_frames:
                self._write_state()
                return
            dt = time.monotonic() - t0
            if dt < period:
                self.sleep(period - dt)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    data = Path(os.environ.get("VITRINE_DATA", "/var/lib/hydrahive2/vitrine"))
    Runner(data_dir=data, fps=int(os.environ.get("VITRINE_FPS", str(DEFAULT_FPS))),
           quality=int(os.environ.get("VITRINE_QUALITY", "80"))).run()


if __name__ == "__main__":
    main()
