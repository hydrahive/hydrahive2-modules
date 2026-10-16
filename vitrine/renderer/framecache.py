"""Bildcache (E4): jedes Video einmal in fertige JPEG-Bilder umrechnen, damit der Dienst zur Laufzeit nicht dekodiert.

Ablage: <cache>/<video>-<schlüssel>.frames/
  frames.bin  – alle JPEGs hintereinander (Restart je MCU-Zeile, siehe jpegrows)
  index.json  – {"version", "count", "w", "h", "fps", "quality", "offsets": [start…, ende]}
Erst in einen .tmp-Ordner schreiben, dann umbenennen: Ein Ordner ohne .tmp ist immer vollständig.
"""
from __future__ import annotations

import hashlib
import json
import mmap
import shutil
from pathlib import Path
from typing import Callable, Iterable, Iterator

from PIL import Image

from . import jpegrows

VERSION = 1


class CacheError(RuntimeError):
    pass


class Cancelled(CacheError):
    pass


def key(src: Path, w: int, h: int, fps: int, quality: int) -> str:
    st = src.stat()
    raw = f"v{VERSION}|{src.name}|{st.st_size}|{int(st.st_mtime)}|{w}x{h}@{fps}|q{quality}"
    return hashlib.sha1(raw.encode()).hexdigest()[:12]


def path_for(src: Path, cache_dir: Path, w: int, h: int, fps: int, quality: int) -> Path:
    return cache_dir / f"{src.stem}-{key(src, w, h, fps, quality)}.frames"


def _drop_old(src: Path, cache_dir: Path, keep: Path) -> None:
    for old in cache_dir.glob(f"{src.stem}-*.frames"):
        if old != keep and old.is_dir():
            shutil.rmtree(old, ignore_errors=True)


def build(src: Path, cache_dir: Path, w: int, h: int, fps: int, quality: int, *,
          frames: Callable[[], Iterable[Image.Image]],
          progress: Callable[[int], None] | None = None,
          cancelled: Callable[[], bool] | None = None) -> Path:
    out = path_for(src, cache_dir, w, h, fps, quality)
    cache_dir.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(out.name + ".tmp")
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir()
    try:
        offsets = [0]
        with open(tmp / "frames.bin", "wb") as fh:
            for img in frames():
                if cancelled and cancelled():
                    raise Cancelled("abgebrochen")
                if img.size != (w, h):
                    raise CacheError(f"Bildgröße {img.size} statt {(w, h)}")
                fh.write(jpegrows.encode(img.convert("RGB"), quality))
                offsets.append(fh.tell())
                if progress:
                    progress(len(offsets) - 1)
        if len(offsets) < 2:
            raise CacheError("Video ohne Bilder")
        (tmp / "index.json").write_text(json.dumps({"version": VERSION, "count": len(offsets) - 1, "w": w, "h": h,
                                                    "fps": fps, "quality": quality, "offsets": offsets}))
        shutil.rmtree(out, ignore_errors=True)
        tmp.rename(out)
    except BaseException:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    _drop_old(src, cache_dir, out)
    return out


class FrameCache:
    def __init__(self, path: Path, offsets: list[int], fh, mm: mmap.mmap):
        self.path, self._off, self._fh, self._mm = path, offsets, fh, mm

    def __len__(self) -> int:
        return len(self._off) - 1

    def __getitem__(self, i: int) -> bytes:
        return self._mm[self._off[i]:self._off[i + 1]]

    def loop(self) -> Iterator[bytes]:
        while True:
            for i in range(len(self)):
                yield self[i]

    def close(self) -> None:
        self._mm.close()
        self._fh.close()


def _valid(idx: dict, size: int, w: int, h: int, fps: int, quality: int) -> bool:
    off = idx.get("offsets")
    if idx.get("version") != VERSION or (idx.get("w"), idx.get("h"), idx.get("fps"), idx.get("quality")) != (w, h, fps, quality):
        return False
    if not isinstance(off, list) or len(off) != idx.get("count", -1) + 1 or len(off) < 2:
        return False
    return off[0] == 0 and off[-1] == size and all(b > a for a, b in zip(off, off[1:]))


def open_cache(src: Path, cache_dir: Path, w: int, h: int, fps: int, quality: int) -> FrameCache | None:
    """Fertigen Cache öffnen; fehlt er oder ist er beschädigt → None (dann wird neu gebaut)."""
    try:
        d = path_for(src, cache_dir, w, h, fps, quality)
        idx = json.loads((d / "index.json").read_text())
        fh = open(d / "frames.bin", "rb")
    except (OSError, ValueError):
        return None
    try:
        size = (d / "frames.bin").stat().st_size
        if not isinstance(idx, dict) or not _valid(idx, size, w, h, fps, quality):
            fh.close()
            return None
        mm = mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ)
        c = FrameCache(d, idx["offsets"], fh, mm)
        for i in (0, len(c) - 1):                         # Stichprobe: Anfang und Ende sind gültige JPEGs
            jpegrows.split(c[i])
        return c
    except (OSError, ValueError, jpegrows.RowsError):
        fh.close()
        return None
