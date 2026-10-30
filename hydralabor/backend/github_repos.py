"""Forks beim Nutzer (PLAN-L2.md Baustein 2).

Ein Repo `<login>/<name>` wird nur benutzt, wenn es ein Fork genau von `hydrahive/<name>` ist. Sonst nichts anfassen
und klar melden. GitHub legt Forks im Hintergrund an → bis 60 s nachsehen.
"""
from __future__ import annotations

import asyncio

from . import github_api
from .github_api import API, GitHubError

TARGETS = {"core": "hydrahive/hydrahive2.0", "modules": "hydrahive/hydrahive2-modules"}
_TRIES = 12
_STEP = 5.0


def _raise_for(st: int, hdr: dict, code: str) -> None:
    if st in (403, 429) and hdr.get("x-ratelimit-remaining") == "0":
        raise GitHubError("labor_github_rate_limited")
    raise GitHubError(code)


async def _fork_state(token: str, full: str, parent: str) -> bool:
    """True = passender Fork da, False = gibt es nicht. Gleichnamig, aber falsch → Fehler."""
    st, body, hdr = await github_api.request("GET", f"{API}/repos/{full}", token=token)
    if st == 404:
        return False
    if st != 200:
        _raise_for(st, hdr, "labor_github_failed")
    if not body.get("fork") or (body.get("parent") or {}).get("full_name") != parent:
        raise GitHubError("labor_github_name_taken")
    return True


async def ensure_fork(token: str, login: str, target: str) -> str:
    parent = TARGETS[target]
    full = f"{login}/{parent.split('/')[1]}"
    if await _fork_state(token, full, parent):
        return full
    st, _, hdr = await github_api.request("POST", f"{API}/repos/{parent}/forks", token=token,
                                          json={"default_branch_only": True})
    if st not in (200, 202):
        _raise_for(st, hdr, "labor_github_fork_failed")
    for _ in range(_TRIES):
        if await _fork_state(token, full, parent):
            return full
        await asyncio.sleep(_STEP)
    raise GitHubError("labor_github_fork_failed")
