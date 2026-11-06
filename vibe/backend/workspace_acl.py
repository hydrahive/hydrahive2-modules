"""POSIX-ACL für den gemeinsam genutzten Host-/Container-Workspace.

Ein unprivilegierter Incus-Container bildet UID/GID 1000 auf hohe Host-IDs ab.
Der Workspace bleibt Eigentum des HydraHive-Dienstes; ACLs geben zusätzlich genau
dieser abgebildeten Container-Identität Zugriff. So sehen Host und Container
identische Dateien, ohne den Container zu privilegieren oder den Ordner world-writable
zu machen.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import stat
import subprocess
from pathlib import Path

from . import container, incus

CONTAINER_UID = 1000
CONTAINER_GID = 1000


def _run(args: list[str]) -> None:
    binary = shutil.which("setfacl")
    if not binary:
        raise FileNotFoundError("setfacl")
    subprocess.run(
        [binary, *args],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )


def _mapped_id(entries: list[dict], *, uid: bool, value: int) -> int:
    for entry in entries:
        try:
            matching = bool(entry["Isuid"]) is uid
            namespace = int(entry["Nsid"])
            host = int(entry["Hostid"])
            length = int(entry["Maprange"])
        except (KeyError, TypeError, ValueError):
            continue
        if matching and namespace <= value < namespace + length:
            return host + value - namespace
    raise container.VibeError("vibe_workspace_unavailable")


async def _idmap(name: str) -> tuple[int, int]:
    # `next` gilt ab dem nächsten Start (z. B. nach `security.idmap.isolated=true`); `current` ist dann noch die alte
    # Zuordnung. Echte Incus-Probe 6.11.: mit `current` bekam UID 1000 keinen Schreibzugriff.
    for key in ("volatile.idmap.next", "volatile.idmap.current"):
        rc, out, _ = await incus.run("config", "get", name, key)
        if rc != 0 or not out.strip():
            continue
        try:
            entries = json.loads(out)
            if not isinstance(entries, list):
                continue
            return (
                _mapped_id(entries, uid=True, value=CONTAINER_UID),
                _mapped_id(entries, uid=False, value=CONTAINER_GID),
            )
        except (json.JSONDecodeError, TypeError, container.VibeError):
            continue
    raise container.VibeError("vibe_workspace_unavailable")


def _entries(mapped_uid: int, mapped_gid: int, permissions: str) -> str:
    """Sollzustand: genau Hostdienst + abgebildete Container-UID/GID dürfen schreiben; „other“ nie (Lesen bleibt wie
    beim normalen Projektworkspace 2775, `X` = Verzeichnisse ja, Dateien nur wenn ausführbar)."""
    host_uid, host_gid = os.getuid(), os.getgid()
    other = "r-" + permissions[-1]
    return (
        f"u:{mapped_uid}:{permissions},g:{mapped_gid}:{permissions},"
        f"u:{host_uid}:{permissions},g:{host_gid}:{permissions},m:{permissions},o::{other}"
    )


def _reset(args: list[str], entries: str, targets: list[str]) -> None:
    """Erst ALLE erweiterten ACL-Einträge entfernen (`-b`), dann den Sollzustand setzen: so bleiben weder alte
    Principals (z. B. von früheren ID-Maps) noch ein vorhandenes `o+w` bestehen."""
    _run([*args, "-b", "--", *targets])
    _run([*args, "-k", "--", *targets])  # Default-ACL ausdrücklich entfernen, nicht von `-b` abhängig machen
    _run([*args, "-m", entries, "--", *targets])


def _apply(path: Path, mapped_uid: int, mapped_gid: int) -> None:
    try:
        entries = _entries(mapped_uid, mapped_gid, "rwx")
        _reset([], entries, [str(path)])
        _run(["-d", "-m", entries, "--", str(path)])
    except (FileNotFoundError, OSError, subprocess.SubprocessError):
        raise container.VibeError("vibe_workspace_unavailable") from None


def _apply_tree(path: Path, mapped_uid: int, mapped_gid: int) -> None:
    try:
        files = _entries(mapped_uid, mapped_gid, "rwX")
        defaults = _entries(mapped_uid, mapped_gid, "rwx")
        _run(["-R", "-b", "--", str(path)])
        _run(["-R", "-k", "--", str(path)])
        _run(["-R", "-m", files, "--", str(path)])
        directories = [path]
        directories.extend(
            child
            for child in path.rglob("*")
            if child.is_dir() and not child.is_symlink()
        )
        for start in range(0, len(directories), 128):
            batch = [str(item) for item in directories[start : start + 128]]
            _run(["-d", "-b", "--", *batch])
            _run(["-d", "-m", defaults, "--", *batch])
    except (FileNotFoundError, OSError, subprocess.SubprocessError):
        raise container.VibeError("vibe_workspace_unavailable") from None


def _strip_fd(fd: int) -> None:
    info = os.fstat(fd)
    if (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)) and info.st_mode & 0o002:
        try:
            os.fchmod(fd, stat.S_IMODE(info.st_mode) & ~0o002)
        except PermissionError:
            pass  # Besitzer ist die abgebildete Container-UID: das erledigt `workspace._strip_in_container`


def strip_world_write(path: Path) -> None:
    """`o+w` im ganzen Baum entfernen (der Containernutzer kann es mit `chmod 777` selbst setzen).

    Nur über Dateideskriptoren: Jeder Eintrag wird mit `O_NOFOLLOW` relativ zu seinem Verzeichnis geöffnet und über das
    Handle geändert. Tauscht der Container die Datei gegen einen Symlink aus, scheitert das Öffnen oder das Handle zeigt
    weiter auf die ursprüngliche Datei – ein Ziel außerhalb wird nie erreicht. Symlinks, FIFOs und Geräte bleiben
    unberührt; ein Fehler an einem Eintrag bricht nicht ab.
    """
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC
    try:
        root_fd = os.open(path, flags | os.O_DIRECTORY)
    except OSError:
        return
    try:
        _strip_fd(root_fd)
    finally:
        os.close(root_fd)
    for _root, dirs, files, dir_fd in os.fwalk(path, follow_symlinks=False):
        for name in [*dirs, *files]:
            try:
                fd = os.open(name, flags, dir_fd=dir_fd)
            except OSError:
                continue
            try:
                _strip_fd(fd)
            except OSError:
                pass
            finally:
                os.close(fd)


async def configure(name: str, path: Path) -> None:
    """Workspace für Hostdienst und Container-UID/GID 1000 bidirektional öffnen."""
    if not path.is_absolute() or not path.is_dir():
        raise container.VibeError("vibe_workspace_unavailable")
    mapped_uid, mapped_gid = await _idmap(name)
    await asyncio.to_thread(_apply, path, mapped_uid, mapped_gid)
    await asyncio.to_thread(strip_world_write, path)


async def configure_tree(name: str, path: Path) -> None:
    """Pulldaten rekursiv plus Default-ACLs für künftige Dateien freigeben."""
    if not path.is_absolute() or not path.is_dir():
        raise container.VibeError("vibe_workspace_unavailable")
    mapped_uid, mapped_gid = await _idmap(name)
    await asyncio.to_thread(_apply_tree, path, mapped_uid, mapped_gid)
    await asyncio.to_thread(strip_world_write, path)
