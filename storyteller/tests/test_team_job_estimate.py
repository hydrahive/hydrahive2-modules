"""T1e: Kostenschätzung vor dem Start eines Team-Auftrags (grob, nur Kern-Preise)."""
from __future__ import annotations

import pytest
from backend import scenes, storage, team_job_estimate
from backend._files import StoryError
from backend.team import jobs_catalog as cat
from conftest import PROJECT_ID


def _book_with_text(words: int = 1000):
    b = storage.create_book(PROJECT_ID, {"title": "T", "kind": "novel"})
    st = storage.get_structure(PROJECT_ID, b["id"])
    ch = st["parts"][0]["chapters"][0]
    sid = ch["scenes"][0]
    sc = scenes.get_scene(PROJECT_ID, b["id"], sid)
    scenes.save_scene(PROJECT_ID, b["id"], sid, {"text": "Wort " * words}, sc["version"])
    return b["id"], ch["id"], sid


def test_scene_estimate_grows_with_text_and_names_place():
    bid, _cid, sid = _book_with_text(200)
    small = team_job_estimate.estimate(PROJECT_ID, bid, cat.get("check_scene"), sid, model="claude-sonnet-4-6")
    bid2, _c2, sid2 = _book_with_text(4000)
    big = team_job_estimate.estimate(PROJECT_ID, bid2, cat.get("check_scene"), sid2, model="claude-sonnet-4-6")
    assert big["input_tokens"] > small["input_tokens"] > 0
    assert small["output_tokens"] == cat.get("check_scene").out_tokens
    assert small["place_title"] and small["cost_micros"] and big["cost_micros"] > small["cost_micros"]


def test_chapter_estimate_counts_all_scenes_of_the_chapter():
    bid, cid, _sid = _book_with_text(1000)
    one = team_job_estimate.estimate(PROJECT_ID, bid, cat.get("critique_chapter"), cid, model="claude-sonnet-4-6")
    second = scenes.add_scene(PROJECT_ID, bid, cid, "Zweite")["scene"]["id"]
    sc = scenes.get_scene(PROJECT_ID, bid, second)
    scenes.save_scene(PROJECT_ID, bid, second, {"text": "Wort " * 1000}, sc["version"])
    two = team_job_estimate.estimate(PROJECT_ID, bid, cat.get("critique_chapter"), cid, model="claude-sonnet-4-6")
    # zweite Szene mit gleich viel Text → Eingabe wächst um (fast) denselben Textanteil
    assert two["input_tokens"] - one["input_tokens"] >= team_job_estimate.READS * (1000 * 5 // 4)


def test_cost_counts_input_and_output_at_core_prices():
    from backend._cost import cost_micros
    bid, _cid, sid = _book_with_text(100)
    e = team_job_estimate.estimate(PROJECT_ID, bid, cat.get("edit_scene"), sid, model="claude-sonnet-4-6")
    assert e["output_tokens"] == cat.get("edit_scene").out_tokens
    assert e["cost_micros"] == cost_micros("claude-sonnet-4-6", tokens_in=e["input_tokens"],
                                           tokens_out=e["output_tokens"])
    assert e["cost_micros"] > cost_micros("claude-sonnet-4-6", tokens_in=e["input_tokens"], tokens_out=0)


def test_unknown_model_has_no_price_but_tokens():
    bid, _cid, sid = _book_with_text(100)
    e = team_job_estimate.estimate(PROJECT_ID, bid, cat.get("check_scene"), sid, model="irgendwer/modell-x")
    assert e["cost_micros"] is None and e["input_tokens"] > 0


def test_place_must_match_scope():
    bid, cid, sid = _book_with_text(10)
    with pytest.raises(StoryError) as e:
        team_job_estimate.estimate(PROJECT_ID, bid, cat.get("check_scene"), cid, model="m")
    assert e.value.code == "place_not_found"
    with pytest.raises(StoryError):
        team_job_estimate.estimate(PROJECT_ID, bid, cat.get("critique_chapter"), sid, model="m")
