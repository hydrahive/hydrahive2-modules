"""Test-Brücke: führt die `git`-Befehle des Moduls im Temp-Ordner aus, statt per `incus exec` im Container.

Ersetzt NUR den Weg zum Container (`backend.versions._run`). Git selbst ist das echte Git – die Zeitmaschine wird gegen
das Verhalten von echtem Git geprüft, nicht gegen eine Attrappe. Die Brücke nimmt dieselbe Argumentliste wie das Modul
und führt sie mit einer sauberen Umgebung aus (kein Nutzer-Git-Config, keine Hooks).
"""
from __future__ import annotations

import asyncio
import os
from pathlib import Path


def clean_env(home: Path) -> dict[str, str]:
    return {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": str(home), "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_TERMINAL_PROMPT": "0", "LC_ALL": "C.UTF-8",
            "GIT_CEILING_DIRECTORIES": str(home.parent)}


class Bridge:
    """Stand-in für `incus exec <container> --cwd /work … -- <befehl>` auf einem lokalen Ordner."""

    def __init__(self, work: Path) -> None:
        self.work = work
        self.calls: list[list[str]] = []

    async def run(self, argv: list[str], *, timeout: float = 60.0, stdin: bytes | None = None) -> tuple[int, str, str]:
        self.calls.append(list(argv))
        p = await asyncio.create_subprocess_exec(
            *argv, cwd=self.work, env=clean_env(self.work.parent),
            stdin=asyncio.subprocess.PIPE if stdin is not None else asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        out, err = await asyncio.wait_for(p.communicate(stdin), timeout=timeout)
        return p.returncode or 0, out.decode(errors="replace"), err.decode(errors="replace")
