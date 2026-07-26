from __future__ import annotations

from dataclasses import replace

from hydrahive.db.connection import db

from .result_codec import serialize_profile_decision


def mark_challenge(store, owner: str, result_id: str, session_id: str, now=None):
    if not isinstance(session_id, str) or not 1 <= len(session_id) <= 512:
        return None
    timestamp = store._time(now)
    with db(immediate=True) as conn:
        item = store._owned(conn, owner, result_id, timestamp)
        if (
            item is None
            or item.claim_id is not None
            or item.decision.selection_status == "ready"
        ):
            return None
        changed = conn.execute(
            """UPDATE module_mediacenter_results SET selection_session_id=?
               WHERE result_id=? AND owner=? AND claim_id IS NULL""",
            (session_id, result_id, owner),
        ).rowcount
        return replace(item, selection_session_id=session_id) if changed else None


def unlock(store, owner: str, result_id: str, preference: str, session_id=None, now=None):
    timestamp = store._time(now)
    with db(immediate=True) as conn:
        item = store._owned(conn, owner, result_id, timestamp)
        if item is None or item.claim_id is not None:
            return None
        if session_id is not None and item.selection_session_id not in {None, session_id}:
            return None
        decision = item.decision
        expected = (
            decision.resolution
            if decision.selection_status == "quality_preference_required"
            else decision.format
            if decision.selection_status == "format_preference_required"
            else None
        )
        if expected is None or expected.lower() != preference.lower():
            return None
        updated = replace(item, decision=replace(decision, selection_status="ready"))
        changed = conn.execute(
            """UPDATE module_mediacenter_results SET payload_json=?
               WHERE result_id=? AND owner=? AND claim_id IS NULL""",
            (serialize_profile_decision(updated.decision), result_id, owner),
        ).rowcount
        return updated if changed else None
