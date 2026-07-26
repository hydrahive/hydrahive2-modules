from __future__ import annotations

import re
from dataclasses import replace

from .config import GERMAN_CATEGORIES
from .models import MediaType, ProfileDecision, RawRelease
from .profile_rules import (
    AUDIO_ALLOWED,
    AUDIOPLAY_TOKENS,
    BOOK_ALLOWED,
    FORBIDDEN_PAIRS,
    FORBIDDEN_SINGLE,
    GERMAN_TOKENS,
    INCOMPLETE_TOKENS,
    KNOWN_DISALLOWED_FORMATS,
    MUSIC_ALLOWED,
    SAMPLE_TOKENS,
)


def _ascii_title(title: str) -> str:
    replacements = {"Ä": "AE", "Ö": "OE", "Ü": "UE", "ẞ": "SS", "ß": "SS"}
    normalized = title.upper()
    for source, target in replacements.items():
        normalized = normalized.replace(source, target)
    return normalized


def _tokens(title: str) -> list[str]:
    return re.findall(r"[A-Z0-9]+", _ascii_title(title))


def _has_pair(tokens: list[str], pairs: set[tuple[str, str]]) -> bool:
    return any((left, right) in pairs for left, right in zip(tokens, tokens[1:]))


def _german(release: RawRelease, token_set: set[str]) -> tuple[bool, str | None]:
    language = (release.language or "").lower().replace("_", "-")
    if (
        release.category_id in GERMAN_CATEGORIES
        or language in {"de", "de-de", "ger", "german", "deutsch"}
        or bool(token_set & GERMAN_TOKENS)
    ):
        return True, "de"
    if language and language not in {"multi", "mul", "unknown"}:
        return False, language.split("-", 1)[0]
    return False, "multi" if "MULTI" in token_set else None


def _resolution(token_set: set[str]) -> str | None:
    if "2160P" in token_set or "UHD" in token_set:
        return "2160p"
    if "1080P" in token_set:
        return "1080p"
    if "1080I" in token_set:
        return "1080i"
    return None


def _format(token_set: set[str], allowed: dict[str, str]) -> str | None:
    return next((value for token, value in allowed.items() if token in token_set), None)


def _bitrate(title: str) -> int | None:
    match = re.search(r"(?<!\d)(\d{2,4})\s*(?:KBIT|KBPS)(?![A-Z])", _ascii_title(title))
    if not match:
        return None
    value = int(match.group(1))
    return value if 8 <= value <= 2_000 else None


def _video(release: RawRelease, tokens: list[str], token_set: set[str]) -> ProfileDecision:
    reasons: list[str] = []
    language_ok, language = _german(release, token_set)
    if language_ok:
        reasons.append("language_confirmed")
    else:
        reasons.append(
            "language_unconfirmed" if language in {None, "multi"} else "language_not_german"
        )

    resolution = _resolution(token_set)
    if resolution:
        reasons.append("resolution_allowed")
    elif token_set & {"720P", "576P", "576I", "480P", "480I", "SD"}:
        reasons.append("resolution_below_minimum")
    else:
        reasons.append("resolution_unknown")

    if token_set & FORBIDDEN_SINGLE or _has_pair(tokens, FORBIDDEN_PAIRS):
        reasons.append("forbidden_source")
    if release.download_url is None:
        reasons.append("download_reference_invalid")

    rejected = {
        "language_not_german", "language_unconfirmed", "resolution_below_minimum",
        "resolution_unknown", "forbidden_source", "download_reference_invalid",
    }
    decision = "rejected" if rejected & set(reasons) else "eligible"
    score = 0 if decision == "rejected" else 100 + (20 if resolution == "2160p" else 10)
    return ProfileDecision(
        release, "movie", decision, tuple(reasons), language, resolution, None, None, score
    )


def _book(release: RawRelease, token_set: set[str]) -> ProfileDecision:
    language_ok, language = _german(release, token_set)
    fmt = _format(token_set, BOOK_ALLOWED)
    reasons = ["language_confirmed" if language_ok else "language_not_german"]
    if fmt:
        reasons.append("format_allowed")
    elif token_set & KNOWN_DISALLOWED_FORMATS:
        reasons.append("format_not_allowed")
    else:
        reasons.append("format_unknown")
    if release.download_url is None:
        reasons.append("download_reference_invalid")
    decision = "eligible" if language_ok and fmt and release.download_url else "rejected"
    score = 0 if decision == "rejected" else 110 if fmt == "epub" else 105
    return ProfileDecision(release, "book", decision, tuple(reasons), language, None, fmt, None, score)


def _spoken_audio(
    release: RawRelease, media_type: MediaType, token_set: set[str]
) -> ProfileDecision:
    language_ok, language = _german(release, token_set)
    fmt = _format(token_set, AUDIO_ALLOWED)
    reasons = ["language_confirmed" if language_ok else "language_not_german"]
    if fmt:
        reasons.append("format_allowed")
    elif token_set & KNOWN_DISALLOWED_FORMATS:
        reasons.append("format_not_allowed")
    else:
        reasons.append("format_unknown")
    if token_set & SAMPLE_TOKENS:
        reasons.append("sample_release")
    if token_set & INCOMPLETE_TOKENS:
        reasons.append("incomplete_release")
    is_play = bool(token_set & AUDIOPLAY_TOKENS) or {"AUDIO", "DRAMA"} <= token_set
    if (media_type == "audioplay" and not is_play) or (media_type == "audiobook" and is_play):
        reasons.append("media_type_mismatch")
    if release.download_url is None:
        reasons.append("download_reference_invalid")
    blocked = {
        "language_not_german", "format_not_allowed", "format_unknown", "sample_release",
        "incomplete_release", "media_type_mismatch", "download_reference_invalid",
    }
    decision = "rejected" if blocked & set(reasons) else "eligible"
    score = 0 if decision == "rejected" else 110 if fmt == "mp3" else 108
    return ProfileDecision(release, media_type, decision, tuple(reasons), language, None, fmt, _bitrate(release.title), score)


def _music(release: RawRelease, token_set: set[str]) -> ProfileDecision:
    fmt = _format(token_set, MUSIC_ALLOWED)
    if fmt:
        reasons = ["format_allowed"]
    elif token_set & KNOWN_DISALLOWED_FORMATS:
        reasons = ["format_not_allowed"]
    else:
        reasons = ["format_unknown"]
    if release.download_url is None:
        reasons.append("download_reference_invalid")
    decision = "eligible" if fmt and release.download_url else "rejected"
    bitrate = _bitrate(release.title) if fmt == "mp3" else None
    score = 0 if decision == "rejected" else 100 + (bitrate or 0) // 32
    return ProfileDecision(release, "music", decision, tuple(reasons), release.language, None, fmt, bitrate, score)


def classify_release(release: RawRelease, media_type: MediaType) -> ProfileDecision:
    tokens = _tokens(release.title)
    token_set = set(tokens)
    if media_type in {"movie", "tv"}:
        result = _video(release, tokens, token_set)
        return replace(result, media_type=media_type)
    if media_type == "book":
        return _book(release, token_set)
    if media_type in {"audiobook", "audioplay"}:
        return _spoken_audio(release, media_type, token_set)
    return _music(release, token_set)


def set_selection_status(
    results: list[ProfileDecision], media_type: MediaType
) -> list[ProfileDecision]:
    eligible = [result for result in results if result.decision == "eligible"]
    status = "ready"
    if media_type in {"movie", "tv"}:
        resolutions = {result.resolution for result in eligible}
        if resolutions & {"1080p", "1080i"} and "2160p" in resolutions:
            status = "quality_preference_required"
    elif media_type == "music":
        formats = {result.format for result in eligible}
        if {"flac", "mp3"} <= formats:
            status = "format_preference_required"
    return [
        replace(result, selection_status=status) if result.decision == "eligible" else result
        for result in results
    ]
