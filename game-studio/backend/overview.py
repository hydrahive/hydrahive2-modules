"""Privacy-minimised overview data for the Game Studio landing page."""

from __future__ import annotations

import sqlite3

from hydrahive.db.connection import db
from hydrahive.samba import samba_status

from . import projects


def _workstation_status() -> dict:
    try:
        with db() as conn:
            nodes = conn.execute(
                """SELECT status, COUNT(*) AS amount FROM compute_nodes
                   WHERE kind = 'agent' GROUP BY status"""
            ).fetchall()
            ready_approvals = conn.execute(
                """SELECT COUNT(*) FROM compute_game_isolation_approvals AS approval
                   JOIN compute_nodes AS node ON node.node_id = approval.node_id
                   WHERE approval.status = 'active' AND node.status IN ('online', 'degraded')"""
            ).fetchone()[0]
    except sqlite3.OperationalError:
        return {"code": "core_update_required", "ready": False, "build_available": False}
    counts = {row["status"]: row["amount"] for row in nodes}
    connected = counts.get("online", 0) + counts.get("degraded", 0)
    if not nodes:
        code = "not_connected"
    elif connected == 0:
        code = "offline"
    elif ready_approvals == 0:
        code = "approval_required"
    else:
        code = "ready_for_binding"
    return {"code": code, "ready": code == "ready_for_binding", "build_available": False}


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
        "workstation": _workstation_status(),
        "runner": {"code": "runner_pending_pr4", "build_available": False},
    }
