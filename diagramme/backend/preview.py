"""Vorschaubilder (Spec §12.3): Bildschirmfoto der Diagramm-Seite mit Chromium. Nie Pflicht – ohne Bild bleibt alles."""
from __future__ import annotations

import logging
import os
import subprocess

from . import chrome, store

logger = logging.getLogger(__name__)
TIMEOUT_SECONDS = 60
FILE = "vorschau.png"
_PASS_ENV = ("PATH", "HOME", "LANG", "LC_ALL", "TMPDIR")


def _run(argv: list[str], *, timeout: int, env: dict[str, str]) -> int:
    done = subprocess.run(argv, timeout=timeout, env=env, capture_output=True, stdin=subprocess.DEVNULL, check=False)
    return done.returncode


def make(view_id: str) -> bool:
    """Bild erzeugen und Zustand merken (ok | fehlt | fehler). True nur bei vorhandenem Bild."""
    if store.get(view_id) is None:
        return False
    exe = chrome.find()
    if not exe:
        store.set_preview_state(view_id, "fehlt")
        return False
    folder = store.root() / view_id
    out = folder / FILE
    argv = [exe, "--headless=new", "--no-sandbox", "--disable-gpu", "--hide-scrollbars", "--window-size=1200,750",
            "--virtual-time-budget=3000", f"--screenshot={out}", f"file://{folder / 'diagramm.html'}"]
    env = {k: os.environ[k] for k in _PASS_ENV if k in os.environ}
    try:
        code = _run(argv, timeout=TIMEOUT_SECONDS, env=env)
    except (subprocess.TimeoutExpired, OSError) as e:
        logger.warning("Diagramme: Vorschaubild %s fehlgeschlagen: %s", view_id, type(e).__name__)
        code = 1
    ok = code == 0 and out.is_file() and out.stat().st_size > 0
    if not ok and out.exists():
        out.unlink()
    store.set_preview_state(view_id, "ok" if ok else "fehler")
    return ok


def path_if_ready(view_id: str):
    """Pfad zum Bild – fehlt es und wurde nie versucht, jetzt einmal erzeugen."""
    row = store.get(view_id)
    if row is None:
        return None
    out = store.root() / view_id / FILE
    if row["preview_state"] is None and not out.is_file():
        make(view_id)
    return out if out.is_file() else None
