"""Datenweg für die Workspace-Migration: `/work` als tar-Strom aus dem Container, sicher auf dem Host entpackt.

Warum nicht `incus file pull -r`: Ein FIFO im Container ließ den Daemon-Helfer (`incusd forkfile`, root) endlos hängen
(echter Vorfall 6.11.). `tar` öffnet FIFOs nie, und Sockets überspringt es. Entpackt wird mit eigener Prüfung statt
`extractall`: keine absoluten oder `..`-Pfade, nie durch einen Symlink hindurch, FIFOs/Geräte werden abgelehnt (nichts
raten), Setuid/Setgid werden verworfen. Grenzen für Mitgliederzahl, Gesamtgröße, Pfadtiefe und Namenslänge schützen
den Host vor Archivbomben (auch Sparse-Mitglieder: die DEKLARIERTE Größe zählt, nicht die Archivgröße). Jede
unerwartete Ausnahme wird zu `vibe_workspace_migration_failed`; nichts verlässt `extract()` roh.
"""

from __future__ import annotations

import math
import os
import shutil
import stat
import tarfile
from pathlib import Path, PurePosixPath

from . import container, incus, workspace_mount

MAX_MEMBERS = 500_000                  # Einträge je Archiv (ein Projekt mit node_modules hat einige Zehntausend)
MAX_TOTAL_BYTES = 8 << 30              # Summe der deklarierten Dateigrößen (Projektgrenze 5 GB plus Luft)
MAX_DEPTH = 128                        # Pfadkomponenten
MAX_NAME = 4096                        # Zeichen je Pfad
MIN_TIME, MAX_TIME = 0.0, 4102444800.0  # 1970 … 2100: alles andere wird auf diese Grenzen gesetzt


async def stream(name: str, archive: Path) -> None:
    """tar von `/work` des (laufenden) Containers in eine Datei auf dem Host."""
    rc, _err = await incus.run_to_file(
        "exec", name, "--", "tar", "-C", workspace_mount.TARGET, "--numeric-owner", "-cf", "-", ".",
        out_path=archive,
    )
    if rc != 0:  # auch rc 1 („Datei hat sich beim Lesen geändert“): lieber nochmal als etwas Halbes übernehmen
        raise container.VibeError("vibe_workspace_migration_failed")


def _fail(code: str = "vibe_workspace_migration_failed") -> container.VibeError:
    return container.VibeError(code)


def _parts(name: str) -> tuple[str, ...]:
    if len(name) > MAX_NAME or "\x00" in name:
        raise _fail("vibe_workspace_too_large" if len(name) > MAX_NAME else "vibe_workspace_migration_failed")
    pure = PurePosixPath(name)
    parts = tuple(p for p in pure.parts if p not in ("", "."))
    if pure.is_absolute() or ".." in parts:
        raise _fail()
    if len(parts) > MAX_DEPTH:
        raise _fail("vibe_workspace_too_large")
    return parts


def _link_parts(name: str) -> tuple[str, ...]:
    """Ziel eines Hardlinks: muss ein echter Pfad im Baum sein (nie leer, nie „.“)."""
    parts = _parts(name)
    if not parts:
        raise _fail()
    return parts


def _time(value: float) -> float:
    """Zeitstempel aus dem Archiv auf einen gültigen Bereich begrenzen (NaN/inf/riesig/negativ → Grenzen)."""
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return MIN_TIME
    if math.isnan(number):
        return MIN_TIME
    return min(max(number, MIN_TIME), MAX_TIME)


def _real_dirs_only(root: Path, parts: tuple[str, ...]) -> Path:
    """Alle Elternverzeichnisse müssen echte Verzeichnisse sein (nie ein Symlink); fehlende werden angelegt."""
    current = root
    for part in parts[:-1]:
        current = current / part
        try:
            info = os.lstat(current)
        except FileNotFoundError:
            os.mkdir(current, 0o700)
            continue
        if not stat.S_ISDIR(info.st_mode):
            raise _fail()
    return current / parts[-1]


def _make_dir(path: Path) -> None:
    """Verzeichnis anlegen. Ein vorhandener Eintrag muss ein ECHTES Verzeichnis sein – nie ein Symlink (Review 4:
    `mkdir(exist_ok=True)` akzeptierte einen Symlink auf ein Verzeichnis, das spätere `chmod` folgte ihm hinaus)."""
    try:
        os.mkdir(path, 0o700)
    except FileExistsError:
        if not stat.S_ISDIR(os.lstat(path).st_mode):
            raise _fail() from None


def _write(handle, target: Path, mode: int, mtime: float) -> None:
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as out:
        shutil.copyfileobj(handle, out, 1 << 20)
        out.flush()  # erst alle Daten ins Dateisystem, sonst überschreibt das Schließen die Zeit mit „jetzt“
        os.fchmod(out.fileno(), (mode & 0o777) | 0o600)  # nie Setuid/Setgid; lesbar für den Hostdienst
        stamp = _time(mtime)
        os.utime(out.fileno(), (stamp, stamp))


def _finish_dir(path: Path, mode: int, mtime: float) -> None:
    """Rechte und Zeit eines Verzeichnisses setzen – ohne je einem Symlink zu folgen (Handle mit O_NOFOLLOW)."""
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        os.fchmod(fd, mode)
        stamp = _time(mtime)
        os.utime(fd, (stamp, stamp))
    finally:
        os.close(fd)


class _Budget:
    """Zählt Mitglieder und deklarierte Größe; überschreitet das Archiv eine Grenze, wird abgebrochen."""

    def __init__(self) -> None:
        self.members = 0
        self.total = 0

    def take(self, member: tarfile.TarInfo) -> None:
        self.members += 1
        if self.members > MAX_MEMBERS:
            raise _fail("vibe_workspace_too_large")
        if member.isreg():
            size = max(int(member.size), 0)
            self.total += size
            if size > MAX_TOTAL_BYTES or self.total > MAX_TOTAL_BYTES:
                raise _fail("vibe_workspace_too_large")


def _one(tar: tarfile.TarFile, member: tarfile.TarInfo, root: Path, dirs: list) -> None:
    parts = _parts(member.name)
    if not parts:
        return
    path = _real_dirs_only(root, parts)
    if member.isdir():
        _make_dir(path)
        dirs.append((path, (member.mode & 0o777) | 0o700, member.mtime))
    elif member.isreg():
        handle = tar.extractfile(member)
        if handle is None:
            raise _fail()
        _write(handle, path, member.mode, member.mtime)
    elif member.issym():
        os.symlink(member.linkname, path)  # nie verfolgt, nur abgelegt
    elif member.islnk():
        source = _real_dirs_only(root, _link_parts(member.linkname))
        info = os.lstat(source)
        if not stat.S_ISREG(info.st_mode):
            raise _fail()
        os.link(source, path)
    elif member.isfifo() or member.ischr() or member.isblk():
        raise _fail("vibe_workspace_special_files")
    else:
        raise _fail()


def extract(archive: Path, target: Path, cancel=None) -> Path:
    """Archiv nach `target/work` entpacken und diesen Ordner zurückgeben. Wirft nur `VibeError`; ein gesetztes
    `cancel` (threading.Event) bricht vor dem nächsten Eintrag ab."""
    try:
        if target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True, mode=0o700)
        root = target / "work"
        root.mkdir(mode=0o700)
        dirs: list[tuple[Path, int, float]] = []
        budget = _Budget()
        with tarfile.open(archive, mode="r|") as tar:
            for member in tar:
                if cancel is not None and cancel.is_set():
                    raise _fail()
                budget.take(member)
                _one(tar, member, root, dirs)
        for path, mode, mtime in reversed(dirs):
            _finish_dir(path, mode, mtime)
    except container.VibeError:
        raise
    except Exception:  # noqa: BLE001 – Grenze: TarError, OSError, ValueError, OverflowError, IndexError … nie roh weiter
        raise _fail() from None
    return root
