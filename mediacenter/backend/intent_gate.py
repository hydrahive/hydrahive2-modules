from __future__ import annotations

import re

from . import action_grants
from .errors import IndexerResponseError
from .result_store import RESULTS

_DIRECT_ACTION = re.compile(
    r"^\s*(?:(?:bitte|please)\s+)?(?:lade|herunterladen|downloade?|download|hole?|nimm|nehme|"
    r"zieh(?:e)?|enqueue)\b",
    re.IGNORECASE,
)
_NEGATED = re.compile(
    r"\b(?:nicht\w*|kein\w*|nichts|niemals|nie|ohne|weder|never|without|not|no|"
    r"nothing|neither|nobody|cannot|avoid|refrain|stop)\b|"
    r"\b\w+n['’]?t\b|\bauf\s+keinen\s+fall\b",
    re.IGNORECASE,
)
_QUALITY = {
    "1080p": {"1080p"},
    "1080i": {"1080i"},
    "2160p": {"2160p", "uhd"},
}
_FORMATS = {"flac", "mp3"}


def has_download_intent(trusted_turn: str | None) -> bool:
    if not isinstance(trusted_turn, str) or not trusted_turn.strip():
        return False
    if _NEGATED.search(trusted_turn):
        return False
    return _DIRECT_ACTION.search(trusted_turn) is not None


def _preference(turn: str, selection_status: str, expected: str | None) -> str | None:
    lowered = turn.casefold()
    if selection_status == "quality_preference_required":
        found = {
            canonical for canonical, aliases in _QUALITY.items()
            if any(re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", lowered) for alias in aliases)
        }
    elif selection_status == "format_preference_required":
        found = {
            value for value in _FORMATS
            if re.search(rf"(?<!\w){value}(?!\w)", lowered)
        }
    else:
        return None
    if len(found) != 1 or expected is None or expected.casefold() not in found:
        return None
    return next(iter(found))


def authorize_enqueue(
    *, owner: str, session_id: str, result_id: str,
    trusted_turn: str | None, trusted_turn_id: str | None,
) -> str:
    if not trusted_turn_id or not has_download_intent(trusted_turn):
        raise IndexerResponseError("confirmation_required")
    item = RESULTS.get(owner, result_id)
    if item is None or item.decision.decision != "eligible":
        raise IndexerResponseError("result_unavailable")
    decision = item.decision
    if decision.selection_status != "ready":
        expected = (
            decision.resolution
            if decision.selection_status == "quality_preference_required"
            else decision.format
        )
        preference = _preference(trusted_turn or "", decision.selection_status, expected)
        if preference is None:
            raise IndexerResponseError(decision.selection_status)
        item = RESULTS.unlock_selection(owner, result_id, preference)
        if item is None:
            raise IndexerResponseError("result_unavailable")
    return action_grants.issue(
        owner=owner, session_id=session_id, result_id=result_id,
        media_type=item.decision.media_type, trusted_turn=trusted_turn or "",
        trusted_turn_id=trusted_turn_id,
    )
