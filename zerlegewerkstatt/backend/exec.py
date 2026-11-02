"""Begrenzte Befehlsausfuehrung ohne Shell.

Jeder Aufruf bekommt ein Zeitlimit und eine Ausgabegrenze. Bei Ueberschreitung
wird die ganze Prozessgruppe beendet, damit keine Analyseprozesse
zurueckbleiben. Es wird nie eine Shell benutzt.
"""
from __future__ import annotations

import logging
import os
import signal
import subprocess
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)

MAX_OUTPUT_BYTES = 8 * 1024 * 1024
#: Nach dem SIGTERM wird so lange gewartet, bevor SIGKILL kommt.
KILL_GRACE = 5


class ExecError(RuntimeError):
    """Der Befehl konnte nicht gestartet werden."""


@dataclass
class CommandResult:
    """Ergebnis eines begrenzten Aufrufs."""

    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False
    truncated: bool = False
    duration_seconds: float = 0.0


def _kill_group(process: subprocess.Popen) -> None:
    """Prozessgruppe beenden, damit keine Kindprozesse zurueckbleiben."""
    try:
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
    except (OSError, ProcessLookupError):
        return
    try:
        process.wait(timeout=KILL_GRACE)
        return
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
    except (OSError, ProcessLookupError):
        return
    try:
        process.wait(timeout=KILL_GRACE)
    except subprocess.TimeoutExpired:
        logger.warning("Analyseprozess liess sich nicht beenden: pid=%s", process.pid)


def run(command: list[str], *, timeout: float, cwd: str | None = None) -> CommandResult:
    """Befehl ohne Shell ausfuehren, Zeitlimit und Ausgabegrenze beachten."""
    started = time.monotonic()
    try:
        process = subprocess.Popen(  # noqa: S603 - Argumentliste, kein Shell
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            cwd=cwd,
            start_new_session=True,
        )
    except FileNotFoundError:
        raise ExecError("runtime_missing") from None
    except OSError:
        raise ExecError("runtime_start_failed") from None

    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        _kill_group(process)
        stdout, stderr = process.communicate()

    truncated = False
    if len(stdout) > MAX_OUTPUT_BYTES:
        stdout = stdout[:MAX_OUTPUT_BYTES]
        truncated = True
    if len(stderr) > MAX_OUTPUT_BYTES:
        stderr = stderr[:MAX_OUTPUT_BYTES]
        truncated = True
    return CommandResult(
        returncode=process.returncode if process.returncode is not None else -1,
        stdout=stdout.decode(errors="replace"),
        stderr=stderr.decode(errors="replace"),
        timed_out=timed_out,
        truncated=truncated,
        duration_seconds=time.monotonic() - started,
    )
