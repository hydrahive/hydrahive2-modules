from __future__ import annotations

import time
from dataclasses import replace


def mark_challenge(store, owner: str, result_id: str, session_id: str, now=None):
    timestamp = time.monotonic() if now is None else now
    with store._lock:
        item = store._owned(owner, result_id, timestamp)
        if (
            item is None
            or item.claim_id is not None
            or item.decision.selection_status == "ready"
        ):
            return None
        updated = replace(item, selection_session_id=session_id)
        store._items[result_id] = updated
        return updated


def unlock(store, owner: str, result_id: str, preference: str, session_id=None, now=None):
    timestamp = time.monotonic() if now is None else now
    with store._lock:
        item = store._owned(owner, result_id, timestamp)
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
        store._items[result_id] = updated
        return updated
