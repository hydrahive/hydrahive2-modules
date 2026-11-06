"""Inhaltsvergleich zweier Verzeichnisbäume für die Workspace-Migration (nur lesend, Symlinks werden nie verfolgt).

Verglichen werden Pfad, Art, Rechte (Modus), erweiterte Attribute sowie bei Symlinks das Ziel und bei normalen Dateien
der Inhalt (SHA-256). FIFOs, Sockets und Geräte werden nie geöffnet (ein FIFO würde das Lesen blockieren), nur nach
Art und Modus verglichen.
"""

from __future__ import annotations

import hashlib
import os
import stat
from pathlib import Path


def _xattrs(path: Path) -> tuple:
    try:
        names = sorted(os.listxattr(path, follow_symlinks=False))
        return tuple((n, os.getxattr(path, n, follow_symlinks=False)) for n in names)
    except OSError:
        return ()  # Dateisystem ohne xattr: auf beiden Seiten gleich leer


def _digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def entries(root: Path) -> dict[str, tuple]:
    """Relativer Pfad → (Art, Modus, Inhaltsnachweis, Attribute)."""
    result: dict[str, tuple] = {}
    for current, dirs, files in os.walk(root, followlinks=False):
        base = Path(current)
        for name in [*dirs, *files]:
            child = base / name
            info = os.lstat(child)
            mode = stat.S_IMODE(info.st_mode)
            if stat.S_ISLNK(info.st_mode):
                proof = ("l", 0, os.readlink(child), ())  # Symlink-Modus ist unter Linux bedeutungslos
            elif stat.S_ISDIR(info.st_mode):
                proof = ("d", mode, "", _xattrs(child))
            elif stat.S_ISREG(info.st_mode):
                proof = ("f", mode, _digest(child), _xattrs(child))
            else:
                proof = ("s", mode, str(stat.S_IFMT(info.st_mode)), ())  # FIFO/Socket/Gerät: nur Art
            result[str(child.relative_to(root))] = proof
    return result


def same_tree(first: Path, second: Path) -> bool:
    """Gleiche Pfade, Arten, Modi, Attribute, Linkziele und Dateiinhalte."""
    return entries(first) == entries(second)
