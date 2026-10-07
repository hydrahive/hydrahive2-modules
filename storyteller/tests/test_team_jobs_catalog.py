"""T1e: Knöpfe im Reiter „Team“ – welcher Helfer, welcher Bereich, welcher Auftragstext (Plan schreib-team-t1e.md)."""
from __future__ import annotations

import pytest

from backend import team
from backend._files import StoryError
from backend.team import jobs_catalog as cat


def test_five_buttons_with_known_roles_and_scopes():
    assert [j.key for j in cat.JOBS] == ["check_scene", "edit_scene", "critique_chapter", "structure_chapter",
                                        "update_profiles"]
    roles = {r.key for r in team.HELPERS}
    for j in cat.JOBS:
        assert j.role in roles and j.scope in ("scene", "chapter") and j.label and j.out_tokens > 0


def test_research_and_creative_have_no_button():
    assert {"research", "creative"}.isdisjoint({j.role for j in cat.JOBS})


def test_get_unknown_job_is_an_error():
    with pytest.raises(StoryError) as e:
        cat.get("delete_book")
    assert e.value.code == "job_unknown"


def test_task_text_names_book_place_and_how_to_deliver():
    text = cat.task_text(cat.get("check_scene"), book_id="b1", book_title="Der Leuchtturm",
                         place_id="s1", place_title="Am Hafen")
    assert "b1" in text and "s1" in text and "„Am Hafen“" in text and "Der Leuchtturm" in text
    assert "storyteller_note" in text            # Ergebnis ablegen, nicht nur antworten
    assert "scene_id" in text                     # Szene als Stelle angeben


def test_chapter_jobs_use_chapter_id():
    text = cat.task_text(cat.get("critique_chapter"), book_id="b1", book_title="T", place_id="c1",
                         place_title="Kapitel 1")
    assert "chapter_id" in text and "c1" in text


def test_editor_and_profiles_deliver_proposals():
    assert "storyteller_propose_text" in cat.task_text(cat.get("edit_scene"), book_id="b", book_title="T",
                                                        place_id="s", place_title="S")
    assert "storyteller_propose_entity" in cat.task_text(cat.get("update_profiles"), book_id="b", book_title="T",
                                                          place_id="s", place_title="S")


def test_task_text_never_lets_titles_inject_braces():
    text = cat.task_text(cat.get("check_scene"), book_id="b", book_title="{place_id}", place_id="s1",
                         place_title="{book_id}")
    assert "„{book_id}“" in text and "{place_id}" in text   # Titel bleiben wörtlich, nichts wird doppelt ersetzt
