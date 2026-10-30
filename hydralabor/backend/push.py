"""Bündel aus dem Labor in den Fork schieben (PLAN-L2.md Baustein 4) – auf dem Server, nie im Container.

- Arbeits-Repo ist `--bare` in einem frischen Ordner (kein Checkout → keine Dateien/Hooks aus dem Labor auf dem
  Server), danach gelöscht; das Bündel auch.
- Das Bündel wird gegen den Stand von `hydrahive/<repo>` main geprüft und geholt (es enthält nur die neuen Commits).
- Token nur über `GIT_CONFIG_*`-Umgebung als `http.extraHeader` – nie im Befehl, in der URL oder in einer Datei.
- Ziel nur `<login>/<repo>` (Fork), Branch nur `labor/<name>`.
"""
from __future__ import annotations

import asyncio
import base64
import os
import re
import shutil
import tempfile
from pathlib import Path

from .github_repos import TARGETS

_BRANCH = re.compile(r"^labor/[a-z0-9][a-z0-9-]{0,80}$")
_FORK = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]{0,38}/([A-Za-z0-9._-]{1,100})$")
_BASE_ENV = {"GIT_TERMINAL_PROMPT": "0", "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
             "HOME": "/nonexistent", "LANG": "C"}


class PushError(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _remote_url(fork: str) -> str:
    return f"https://github.com/{fork}.git"


def _base_url(target: str) -> str:
    return f"https://github.com/{TARGETS[target]}.git"


async def _git(args: list[str], *, cwd: Path, env: dict[str, str], timeout: float = 300) -> int:
    proc = await asyncio.create_subprocess_exec("git", *args, cwd=str(cwd), env={"PATH": "/usr/bin:/bin", **env},
                                                stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
                                                stdin=asyncio.subprocess.DEVNULL)
    try:
        return await asyncio.wait_for(proc.wait(), timeout=timeout)
    except TimeoutError:
        proc.kill()
        return -1


def _auth_env(token: str) -> dict[str, str]:
    basic = base64.b64encode(f"x-access-token:{token}".encode()).decode()
    return {"GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "http.extraHeader",
            "GIT_CONFIG_VALUE_0": f"Authorization: Basic {basic}"}


def _check(fork: str, target: str, branch: str) -> None:
    m = _FORK.match(fork or "")
    if not m or fork.split("/")[0].lower() == "hydrahive" or m.group(1) != TARGETS[target].split("/")[1]:
        raise PushError("labor_submit_push_failed")
    if not _BRANCH.match(branch or ""):                    # nur a-z0-9 und „-“: keine „..“, „:“, Leerzeichen
        raise PushError("labor_submit_push_failed")


async def push_bundle(bundle: Path, *, fork: str, target: str, branch: str, token: str, workdir: Path) -> None:
    bundle = Path(bundle)
    try:
        _check(fork, target, branch)
        tmp = Path(tempfile.mkdtemp(prefix="push-", dir=workdir))
        try:
            env = dict(_BASE_ENV)
            if await _git(["init", "-q", "--bare", "."], cwd=tmp, env=env) != 0:
                raise PushError("labor_submit_push_failed")
            # Basis (main des Haupt-Repos) holen – öffentlich, ohne Token –, dann das Bündel darauf.
            if await _git(["fetch", "-q", "--depth=200", _base_url(target), "main:refs/base/main"], cwd=tmp,
                          env=env, timeout=600) != 0:
                raise PushError("labor_submit_push_failed")
            if await _git(["fetch", "-q", str(bundle), f"HEAD:refs/heads/{branch}"], cwd=tmp, env=env) != 0:
                raise PushError("labor_submit_bundle_invalid")
            if await _git(["push", "-q", _remote_url(fork), f"refs/heads/{branch}:refs/heads/{branch}"], cwd=tmp,
                          env={**env, **_auth_env(token)}, timeout=600) != 0:
                raise PushError("labor_submit_push_failed")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    finally:
        bundle.unlink(missing_ok=True)
