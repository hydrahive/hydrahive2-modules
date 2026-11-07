"""`/work` des Containers sicher auslesen: zweimal als tar-Strom, entpacken, vergleichen."""

from __future__ import annotations

import asyncio
import shutil
import threading
from pathlib import Path

from . import container, incus, workspace_mount, workspace_tar
from .workspace_state import open_group_bits as _open_group_bits
from .workspace_verify import same_tree as _same_tree

_DEV = "vibe-dev.service"


async def dev_server(name: str, action: str) -> bool:
    """Dev-Server anhalten/starten; True bei Erfolg. Das Anhalten ist best effort (der Doppelvergleich fängt Schreiber)."""
    rc, _, _ = await incus.run("exec", name, "--", "systemctl", action, _DEV, timeout=60)
    return rc == 0


def _extract_and_compare(first: Path, second: Path, root: Path, verify: Path, cancel: threading.Event) -> Path:
    source = workspace_tar.extract(first, root, cancel)
    again = workspace_tar.extract(second, verify, cancel)
    if not _same_tree(source, again):
        raise container.VibeError("vibe_workspace_migration_failed")
    return source


async def _in_thread(first: Path, second: Path, root: Path, verify: Path) -> Path:
    """Entpacken im Thread. Bei Abbruch: Signal setzen und auf das ENDE des Threads warten – erst danach darf
    aufgeräumt werden, sonst legt der noch laufende Thread Staging wieder an."""
    cancel = threading.Event()
    work = asyncio.ensure_future(asyncio.to_thread(_extract_and_compare, first, second, root, verify, cancel))
    try:
        return await asyncio.shield(work)
    except asyncio.CancelledError:
        cancel.set()
        while not work.done():
            try:
                await asyncio.wait({work})
            except asyncio.CancelledError:
                continue
        if not work.cancelled():
            work.exception()  # abholen, sonst Warnung „never retrieved“
        raise


async def read_work(project_id: str, name: str) -> Path:
    """`/work` zweimal als tar-Strom aus dem Container lesen, sicher entpacken und beide Stände vergleichen.

    Der Container läuft dafür (`incus exec`); Agentenläufe sind ruhiggestellt und der Dev-Server angehalten. Ein
    Schreibzugriff zwischen den beiden Strömen macht sie ungleich → Abbruch ohne Veröffentlichung."""
    root = workspace_mount.staging(project_id)
    verify = root.parent / "verify"
    archives = root.parent / "archives"
    shutil.rmtree(archives, ignore_errors=True)
    archives.mkdir(parents=True, mode=0o700)
    first, second = archives / "1.tar", archives / "2.tar"
    try:
        await workspace_tar.stream(name, first)
        await workspace_tar.stream(name, second)
        source = await _in_thread(first, second, root, verify)
    except container.VibeError:
        shutil.rmtree(root, ignore_errors=True)
        raise
    finally:
        shutil.rmtree(verify, ignore_errors=True)
        shutil.rmtree(archives, ignore_errors=True)
    _open_group_bits(source)
    return source
