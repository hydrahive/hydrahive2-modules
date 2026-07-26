from __future__ import annotations

from dataclasses import replace

import pytest

from backend.models import RawRelease
from backend.profiles import classify_release, set_selection_status


def _release(title: str, *, category: int, language: str | None = None) -> RawRelease:
    return RawRelease(
        title=title,
        guid="guid-1",
        category_id=category,
        size_bytes=500_000_000,
        language=language,
        published_at=None,
        download_url="https://treasure-maps.com/getnzb/guid-1",
    )


@pytest.mark.parametrize("title,expected_format", [("Roman.German.EPUB", "epub"), ("Roman.DEUTSCH.PDF", "pdf")])
def test_german_epub_and_pdf_are_allowed(title, expected_format):
    result = classify_release(_release(title, category=7120), "book")

    assert result.decision == "eligible"
    assert result.format == expected_format


@pytest.mark.parametrize("title", ["Roman.German.MOBI", "Roman.German.AZW3", "Roman.German.TXT"])
def test_unsupported_book_formats_are_rejected(title):
    result = classify_release(_release(title, category=7120), "book")

    assert result.decision == "rejected"
    assert {"format_not_allowed", "format_unknown"} & set(result.reasons)


def test_book_requires_confirmed_german_language():
    result = classify_release(_release("Novel.EPUB", category=7000, language="en"), "book")

    assert result.decision == "rejected"
    assert "language_not_german" in result.reasons


@pytest.mark.parametrize("media_type", ["audiobook", "audioplay"])
@pytest.mark.parametrize("audio_format", ["MP3", "M4B"])
def test_german_audio_formats_are_allowed(media_type, audio_format):
    marker = "Hoerspiel" if media_type == "audioplay" else "Hoerbuch"
    result = classify_release(
        _release(f"Titel.German.{marker}.{audio_format}", category=3130), media_type
    )

    assert result.decision == "eligible"
    assert result.format == audio_format.lower()


@pytest.mark.parametrize("marker", ["SAMPLE", "HOERPROBE", "AUSZUG", "INCOMPLETE", "UNVOLLSTAENDIG"])
def test_audio_samples_and_incomplete_releases_are_rejected(marker):
    result = classify_release(
        _release(f"Titel.German.Hoerbuch.MP3.{marker}", category=3130), "audiobook"
    )

    assert result.decision == "rejected"
    assert {"sample_release", "incomplete_release"} & set(result.reasons)


def test_audioplay_requires_audioplay_marker():
    result = classify_release(_release("Titel.German.MP3", category=3130), "audioplay")

    assert result.decision == "rejected"
    assert "media_type_mismatch" in result.reasons


def test_audiobook_rejects_explicit_audioplay():
    result = classify_release(
        _release("Titel.German.Hoerspiel.MP3", category=3130), "audiobook"
    )

    assert result.decision == "rejected"
    assert "media_type_mismatch" in result.reasons


@pytest.mark.parametrize("title,expected_format", [("Artist.Album.FLAC", "flac"), ("Artist.Album.MP3.320kbps", "mp3")])
def test_music_accepts_flac_and_mp3_in_any_language(title, expected_format):
    result = classify_release(_release(title, category=3040 if expected_format == "flac" else 3010, language="en"), "music")

    assert result.decision == "eligible"
    assert result.format == expected_format


def test_music_mp3_extracts_bitrate():
    result = classify_release(_release("Artist.Album.MP3.320kbps", category=3010), "music")
    assert result.bitrate_kbps == 320


def test_music_requires_format_choice_when_flac_and_mp3_exist():
    flac = classify_release(_release("Artist.Album.FLAC", category=3040), "music")
    mp3 = classify_release(
        replace(_release("Artist.Album.MP3.320kbps", category=3010), guid="guid-2"), "music"
    )

    grouped = set_selection_status([flac, mp3], "music")

    assert {item.selection_status for item in grouped} == {"format_preference_required"}


def test_music_single_format_is_ready():
    flac = classify_release(_release("Artist.Album.FLAC", category=3040), "music")
    assert set_selection_status([flac], "music")[0].selection_status == "ready"
