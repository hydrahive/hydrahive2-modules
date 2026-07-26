from __future__ import annotations

import re

from . import action_grants
from .errors import IndexerResponseError
from .result_store import RESULTS

_DIRECT_ACTION = re.compile(
    r"^\s*(?:(?:bitte|please)\s+)?(?:download(?:e)?|enqueue|herunterladen)\b|"
    r"^\s*(?:bitte\s+)?lade\b.{1,120}\bherunter\b",
    re.IGNORECASE,
)
_PREFERENCE_ACTION = re.compile(
    r"^\s*(?:bitte\s+)?(?:nimm|nehme)\b", re.IGNORECASE
)
_NEGATED = re.compile(
    r"\b(?:nicht\w*|kein\w*|nichts|niemals|nie|ohne|weder|never|without|not|no|"
    r"nothing|neither|nobody|cannot|avoid|refrain|stop)\b|"
    r"\b\w+n['’]?t\b|\bauf\s+keinen\s+fall\b",
    re.IGNORECASE,
)
_META = re.compile(
    r"\b(?:übersetz\w*|translate\w*|bedeut\w*|meaning|vergleich\w*|compare|"
    r"information\w*|erklär\w*|explain|angenommen|assume|hypothet\w*|heiß\w*|"
    r"definition\w*|definier\w*|spell|buchstabier\w*)\b|"
    r"\bauf\s+(?:deutsch|englisch)\b|\bin\s+(?:german|english)\b",
    re.IGNORECASE,
)
_QUALITY = {"1080p": {"1080p"}, "1080i": {"1080i"}, "2160p": {"2160p", "uhd"}}
_FORMATS = {"flac", "mp3"}
_STOP = {
    "bitte", "please", "download", "downloade", "enqueue", "herunterladen",
    "lade", "herunter", "diesen", "diese", "dieses", "den", "die", "das",
    "film", "serie", "buch", "hörbuch", "hörspiel", "musik", "version",
    "movie", "show", "book", "music", "take", "nimm", "nehme", "the",
    "1080p", "1080i", "2160p", "uhd", "flac", "mp3", "german", "deutsch",
    "english", "englisch", "web", "webdl", "bluray", "remux", "proper",
    "complete", "x264", "x265", "h264", "h265", "hdr", "dv", "multi",
}


def has_download_intent(trusted_turn: str | None) -> bool:
    if not isinstance(trusted_turn, str) or not trusted_turn.strip():
        return False
    if _NEGATED.search(trusted_turn) or _META.search(trusted_turn):
        return False
    return _DIRECT_ACTION.search(trusted_turn) is not None


def _references_title(turn: str, title: str) -> bool:
    turn_tokens = {
        token for token in re.findall(r"\w+", turn.casefold(), re.UNICODE)
        if len(token) >= 3 and not token.isdigit() and token not in _STOP
    }
    title_tokens = set(re.findall(r"\w+", title.casefold(), re.UNICODE))
    return bool(turn_tokens) and turn_tokens <= title_tokens


def _preference(turn: str, selection_status: str, expected: str | None) -> str | None:
    lowered = turn.casefold()
    candidates = _QUALITY if selection_status == "quality_preference_required" else {
        value: {value} for value in _FORMATS
    } if selection_status == "format_preference_required" else {}
    found = {
        canonical for canonical, aliases in candidates.items()
        if any(re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", lowered) for alias in aliases)
    }
    if len(found) != 1 or expected is None or expected.casefold() not in found:
        return None
    return next(iter(found))


def authorize_enqueue(
    *, owner: str, session_id: str, result_id: str,
    trusted_turn: str | None, trusted_turn_id: str | None,
) -> str:
    if not trusted_turn_id or not isinstance(trusted_turn, str):
        raise IndexerResponseError("confirmation_required")
    item = RESULTS.get(owner, result_id)
    if item is None or item.decision.decision != "eligible":
        raise IndexerResponseError("result_unavailable")
    direct = has_download_intent(trusted_turn)
    title_match = _references_title(trusted_turn, item.decision.release.title)
    decision = item.decision
    if decision.selection_status != "ready":
        expected = decision.resolution if decision.selection_status == "quality_preference_required" else decision.format
        preference = _preference(trusted_turn, decision.selection_status, expected)
        challenged = item.selection_session_id == session_id
        preference_action = (
            _PREFERENCE_ACTION.search(trusted_turn) is not None
            and _NEGATED.search(trusted_turn) is None
            and _META.search(trusted_turn) is None
        )
        if preference is not None and (title_match and direct or challenged and (direct or preference_action)):
            item = RESULTS.unlock_selection(
                owner, result_id, preference, session_id=session_id
            )
            if item is None:
                raise IndexerResponseError("result_unavailable")
        else:
            if direct and title_match:
                RESULTS.mark_selection_challenge(owner, result_id, session_id)
                raise IndexerResponseError(decision.selection_status)
            raise IndexerResponseError("confirmation_required")
    elif not direct or not title_match:
        raise IndexerResponseError("confirmation_required")
    return action_grants.issue(
        owner=owner, session_id=session_id, result_id=result_id,
        media_type=item.decision.media_type, trusted_turn=trusted_turn,
        trusted_turn_id=trusted_turn_id,
    )
