"""Privacy-minimised overview data for workspace-backed Game Studio projects."""

from __future__ import annotations

from hydrahive.samba import samba_status

from . import projects


def _sharing_status() -> dict:
    status = samba_status()
    return {
        "available": bool(status.get("installed")),
        "running": bool(status.get("running")),
        "user": str(status.get("user") or ""),
        "platform": str(status.get("platform") or "linux"),
    }


def overview(username: str, role: str) -> dict:
    return {
        "projects": projects.list_for(username, role),
        "sharing": _sharing_status(),
    }
