"""Bildquelle für den Dienst (E4): fertige JPEGs aus dem Bildcache – sonst der bisherige Weg (dekodieren, kodieren).

`Source.next(overlays)` liefert das nächste JPEG mit eingesetztem Overlay. Solange der Cache gebaut wird, kommen die
Bilder vom Videodekoder; sobald er fertig ist, wird beim nächsten Prüfen umgeschaltet. Ein kaputtes Cache-Bild schaltet
dauerhaft (für dieses Programm) auf den bisherigen Weg zurück, der Dienst läuft weiter.
"""
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Callable, Iterator

from PIL import Image

from . import jpegrows, scene, splice
from .frames import encode

log = logging.getLogger("vitrine.cache")


class Source:
    def __init__(self, video: Path | None, w: int, h: int, fps: int, quality: int, *,
                 frames: Callable[..., Iterator[Image.Image]], warmer, check_every: float = 2.0):
        self.video, self.w, self.h, self.fps, self.q = video, w, h, fps, quality
        self._frames_fn, self._warmer, self.check_every = frames, warmer, check_every
        self._decoded: Iterator[Image.Image] | None = None
        self._cache = None
        self._jpegs: Iterator[bytes] | None = None
        self._checked = -1e18
        self.broken: str | None = None
        self.last_frame: Image.Image | None = None      # nur bisheriger Weg; für die Vorschau

    def _try_cache(self) -> None:
        now = time.monotonic()
        if self._cache is not None or self.broken or self.video is None or self._warmer is None:
            return
        if now - self._checked < self.check_every:
            return
        self._checked = now
        c = self._warmer.get(self.video, self.w, self.h, self.fps, self.q)
        if c is not None and len(c):
            self._cache, self._jpegs, self._decoded = c, c.loop(), None

    def next(self, overlays: list[Image.Image]) -> bytes:
        self._try_cache()
        if self._jpegs is not None:
            raw = next(self._jpegs)
            try:
                self.last_frame = None
                return splice.apply(raw, overlays, self.q)
            except (jpegrows.RowsError, ValueError, OSError) as e:
                self.broken = f"Bildcache unbrauchbar: {e}"
                log.warning(self.broken)
                self.close()
        if self._decoded is None:
            self._decoded = iter(self._frames_fn(self.video, self.w, self.h, self.fps))
        img = next(self._decoded)
        for ov in overlays:
            img = scene.compose(img, ov)
        self.last_frame = img
        return encode(img, self.q)

    @property
    def cached(self) -> bool:
        return self._jpegs is not None

    def close(self) -> None:
        if self._cache is not None:
            self._cache.close()
        self._cache, self._jpegs = None, None
