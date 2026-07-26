from __future__ import annotations

from dataclasses import replace

import pytest

from backend.models import RawRelease
from backend.profiles import classify_release, set_selection_status


def _release(title: str, *, category: int = 2140, language: str | None = None) -> RawRelease:
    return RawRelease(
        title=title,
        guid="guid-1",
        category_id=category,
        size_bytes=10_000_000_000,
        language=language,
        published_at=None,
        download_url="https://treasure-maps.com/getnzb/guid-1",
    )


@pytest.mark.parametrize(
    "title,category,language,resolution",
    [
        ("Der.Pate.1972.German.1080p.BluRay.x264-GRP", 2140, None, "1080p"),
        ("Dune.2024.MULTI.2160p.UHD.BluRay-GRP", 2145, None, "2160p"),
        ("Serie.S01E02.1080i.HDTV-GRP", 9999, "de", "1080i"),
        ("Film.DEUTSCH.UHD.Remux-GRP", 9999, None, "2160p"),
    ],
)
def test_allowed_german_video_releases(title, category, language, resolution):
    result = classify_release(_release(title, category=category, language=language), "movie")

    assert result.decision == "eligible"
    assert result.language == "de"
    assert result.resolution == resolution
    assert "language_confirmed" in result.reasons
    assert "resolution_allowed" in result.reasons


@pytest.mark.parametrize(
    "title,reason",
    [
        ("Film.MULTI.2160p.WEB-DL-GRP", "language_unconfirmed"),
        ("Film.German.720p.WEB-DL-GRP", "resolution_below_minimum"),
        ("Film.German.WEB-DL-GRP", "resolution_unknown"),
    ],
)
def test_video_language_and_resolution_rejections(title, reason):
    result = classify_release(_release(title, category=9999), "movie")

    assert result.decision == "rejected"
    assert reason in result.reasons


@pytest.mark.parametrize(
    "marker",
    [
        "CAM", "CAMRip", "HD-CAM", "TS", "HDTS", "TELESYNC", "TC",
        "TELECINE", "SCR", "SCREENER", "DVD-SCR", "WEBSCREENER", "WORKPRINT", "R5",
    ],
)
def test_forbidden_video_sources_are_rejected(marker):
    result = classify_release(_release(f"Film.German.1080p.{marker}-GRP"), "movie")

    assert result.decision == "rejected"
    assert "forbidden_source" in result.reasons


@pytest.mark.parametrize("word", ["CAMBRIDGE", "SCRATCH", "R5D2", "TSONG"])
def test_forbidden_source_detection_has_basic_false_positive_protection(word):
    result = classify_release(_release(f"Film.German.1080p.{word}-GRP"), "movie")
    assert "forbidden_source" not in result.reasons


def test_video_results_require_quality_choice_when_1080_and_2160_exist():
    low = classify_release(_release("Film.German.1080p.WEB-DL-GRP"), "movie")
    high = classify_release(
        replace(_release("Film.German.2160p.WEB-DL-GRP"), guid="guid-2"), "movie"
    )

    grouped = set_selection_status([low, high], "movie")

    assert {item.selection_status for item in grouped} == {"quality_preference_required"}


def test_single_video_resolution_is_ready():
    result = classify_release(_release("Film.German.1080p.WEB-DL-GRP"), "movie")
    assert set_selection_status([result], "movie")[0].selection_status == "ready"
