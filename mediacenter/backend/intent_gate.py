from __future__ import annotations

import re

from . import action_grants
from .errors import IndexerResponseError
from .result_registry import RESULTS

_DIRECT_ACTION = re.compile(
    r"^\s*(?:(?:bitte|please)\s+)?"
    r"(?:download(?:e)?|enqueue|herunterladen|runterladen|runterlade)\b|"
    r"^\s*(?:bitte\s+)?(?:lade|lad)\b.{1,120}\b(?:herunter|runter)\b",
    re.IGNORECASE,
)
_PREFERENCE_ACTION = re.compile(
    r"^\s*(?:bitte\s+)?(?:nimm|nehme)\b", re.IGNORECASE
)
# Sammel-Download: das Verb darf irgendwo im Satz stehen (nicht nur am Anfang),
# weil natuerliche Sammelbefehle wie "ja, alle runterladen" oder "lad alle Alben
# von X runter" das Verb nicht voranstellen. Der zusaetzliche Schutz gegen
# Prompt-Injection kommt hier NICHT aus dem Satzanfang, sondern daraus, dass der
# Sammelname (Kuenstler/Franchise) im Nutzer-Turn stehen UND in jedem Titel
# auftauchen muss (siehe authorize_batch_enqueue).
_BATCH_ACTION = re.compile(
    r"\b(?:download(?:e|en)?|enqueue|herunterladen|herunterlade|"
    r"runterladen|runterlade|herunter|runter)\b",
    re.IGNORECASE,
)
# Ein Sammel-Quantor macht die Batch-Absicht eindeutig ("alle", "sämtliche",
# "jedes", "komplett", "gesamte", "all(e)"). Ohne ihn faellt der Aufruf auf den
# strengen Einzel-Download-Pfad zurueck.
_COLLECTION_QUANTIFIER = re.compile(
    r"\b(?:alle|allen|aller|sämtliche\w*|saemtliche\w*|jede[nsmr]?|"
    r"komplett\w*|gesamte\w*|all|every|complete|entire|whole)\b",
    re.IGNORECASE,
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


def has_collection_download_intent(trusted_turn: str | None) -> bool:
    """Erkennt einen Sammel-Download ("alle Alben/Filme von X runterladen").

    Anders als ``has_download_intent`` ist das Verb nicht an den Satzanfang
    gebunden — dafuer sind ein Download-Verb UND ein Sammel-Quantor ("alle",
    "sämtliche", ...) noetig. Verneinungen und Meta-Fragen schliessen aus.
    """
    if not isinstance(trusted_turn, str) or not trusted_turn.strip():
        return False
    if _NEGATED.search(trusted_turn) or _META.search(trusted_turn):
        return False
    return bool(
        _BATCH_ACTION.search(trusted_turn)
        and _COLLECTION_QUANTIFIER.search(trusted_turn)
    )


def _identity_tokens(value: str) -> set[str]:
    return {
        token for token in re.findall(r"\w+", value.casefold(), re.UNICODE)
        if (len(token) >= 3 or re.fullmatch(r"(?:19|20)\d{2}", token))
        and token not in _STOP
    }


def _references_title(turn: str, title: str) -> bool:
    turn_tokens = _identity_tokens(turn)
    title_tokens = _identity_tokens(title)
    # Eine einzelne Franchise-/Titelreferenz (z. B. "Dune") ist nicht eindeutig.
    return len(turn_tokens) >= 2 and turn_tokens <= title_tokens


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


def _tokens_subset(value: str, tokens: set[str]) -> bool:
    """True, wenn alle identifizierenden Tokens von ``value`` in ``tokens`` sind."""
    needle = _identity_tokens(value)
    return bool(needle) and needle <= tokens


def authorize_batch_enqueue(
    *, owner: str, session_id: str, collection: str, result_ids: list[str],
    trusted_turn: str | None, trusted_turn_id: str | None,
) -> tuple[dict[str, str], dict[str, str]]:
    """Autorisiert einen Sammel-Download ("alle Alben von X").

    Sicherheitsmodell (Prompt-Injection-fest ohne den Einzel-Download-Pfad
    aufzuweichen):

    * Download-Verb + Sammel-Quantor muessen aus dem NUTZER-Turn kommen.
    * Der Sammelname (``collection``) muss im Nutzer-Turn vorkommen — der Agent
      kann keinen Kuenstler einschmuggeln, den der Nutzer nie genannt hat.
    * Jeder autorisierte Treffer muss die Collection-Tokens IM TITEL tragen —
      ein manipuliertes "DOWNLOAD ME"-Release ohne den Namen faellt raus.
    * Pro Treffer wird ein eigener Grant ausgestellt (Fingerprint mit
      result_id gesalzen), sonst kollidiert die UNIQUE-Bedingung der
      Grant-Tabelle und nur der erste Treffer bekaeme einen gueltigen Grant.

    Gibt ``(authorized, skipped)`` zurueck: ``authorized`` bildet result_id auf
    grant_id ab, ``skipped`` result_id auf einen Grund. Bei ungueltigem Turn
    (keine Sammel-Absicht / Name nicht im Turn) wird ``confirmation_required``
    geworfen — nichts wird autorisiert.
    """
    if not trusted_turn_id or not isinstance(trusted_turn, str):
        raise IndexerResponseError("confirmation_required")
    if not has_collection_download_intent(trusted_turn):
        raise IndexerResponseError("confirmation_required")
    turn_tokens = _identity_tokens(trusted_turn)
    if not _tokens_subset(collection, turn_tokens):
        # Der genannte Sammelname steht nicht im Nutzer-Turn.
        raise IndexerResponseError("collection_not_in_turn")

    authorized: dict[str, str] = {}
    skipped: dict[str, str] = {}
    for result_id in dict.fromkeys(result_ids):
        item = RESULTS.get(owner, result_id)
        if item is None or item.decision.decision != "eligible":
            skipped[result_id] = "result_unavailable"
            continue
        if item.decision.selection_status != "ready":
            # Sammel-Downloads loesen keine Qualitaets-/Format-Rueckfrage auf.
            skipped[result_id] = item.decision.selection_status
            continue
        if not _tokens_subset(collection, _identity_tokens(item.decision.release.title)):
            skipped[result_id] = "collection_title_mismatch"
            continue
        authorized[result_id] = action_grants.issue(
            owner=owner, session_id=session_id, result_id=result_id,
            media_type=item.decision.media_type, trusted_turn=trusted_turn,
            trusted_turn_id=trusted_turn_id, fingerprint_salt=result_id,
        )
    return authorized, skipped
