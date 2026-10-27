"""SMB-Attrappe: Ordnerbaum im Speicher mit echten kleinen Audiodateien (tests/fixtures, 2 s Sinus).

Bildet genau die Schnittstelle nach, die backend/smb_source.py vom Verbindungsobjekt braucht:
`walk()` liefert (rel_dir, [(name, size, mtime), …]) je Ordner, `open(rel_path)` ein Datei-Objekt zum Lesen.
Schreiben gibt es nicht – die Freigabe wird nur gelesen (Plex nutzt sie mit).
"""
from __future__ import annotations

import io
from dataclasses import dataclass, field
from pathlib import Path

from mutagen.easyid3 import EasyID3
from mutagen.flac import FLAC
from mutagen.mp3 import MP3

FIX = Path(__file__).resolve().parent / "fixtures"


def audio(fmt: str = "mp3", **tags: str) -> bytes:
    """Echte MP3/FLAC-Datei (2 s) mit den gewünschten Tags (artist, title, album, genre, date, tracknumber …)."""
    raw = (FIX / f"stille.{fmt}").read_bytes()
    if not tags:
        return raw
    buf = io.BytesIO(raw)
    if fmt == "mp3":
        m = MP3(buf, ID3=EasyID3)
        if m.tags is None:
            m.add_tags()
    else:
        m = FLAC(buf)
    for k, v in tags.items():
        m[k] = v
    buf.seek(0)
    m.save(buf)
    return buf.getvalue()


@dataclass
class FakeShare:
    files: dict[str, tuple[bytes, int]] = field(default_factory=dict)   # rel_path → (inhalt, mtime)
    logins: list[tuple[str, str, str, str]] = field(default_factory=list)  # (host, share, user, password)
    opened: list[str] = field(default_factory=list)
    fail: str | None = None             # "unreachable" | "auth" | "share" beim Verbinden
    broken_open: set[str] = field(default_factory=set)

    def put(self, rel_path: str, data: bytes, mtime: int = 1_700_000_000) -> None:
        self.files[rel_path] = (data, mtime)

    def remove(self, rel_path: str) -> None:
        self.files.pop(rel_path, None)

    def connect(self, host: str, share: str, user: str, password: str, base: str = ""):
        from backend.smb_source import SourceError
        self.logins.append((host, share, user, password))
        if self.fail == "unreachable":
            raise SourceError("radiostream_source_unreachable")
        if self.fail == "auth":
            raise SourceError("radiostream_auth_failed")
        if self.fail == "share":
            raise SourceError("radiostream_share_not_found")
        return _Conn(self, base.strip("/"))


class _Conn:
    def __init__(self, share: FakeShare, base: str):
        self._s, self._base = share, base

    def _visible(self) -> dict[str, tuple[bytes, int]]:
        pre = self._base + "/" if self._base else ""
        return {p[len(pre):]: v for p, v in self._s.files.items() if p.startswith(pre)}

    def top_dirs(self) -> list[str]:
        return sorted({p.split("/", 1)[0] for p in self._visible() if "/" in p})

    def walk(self):
        tree: dict[str, list[tuple[str, int, int]]] = {}
        for rel, (data, mtime) in sorted(self._visible().items()):
            d, _, name = rel.rpartition("/")
            tree.setdefault(d, []).append((name, len(data), mtime))
        for d in sorted(tree):
            yield d, tree[d]

    def open(self, rel_path: str):
        self._s.opened.append(rel_path)
        if rel_path in self._s.broken_open:
            raise OSError("lesen fehlgeschlagen")
        data, _ = self._visible()[rel_path]
        return io.BytesIO(data)

    def close(self) -> None:
        pass
