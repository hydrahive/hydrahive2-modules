"""Studio G1: geführter Weg, Schritt „Idee“ (studio/SPEC.md „Bauplan G1“). Das LLM wird ersetzt."""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

from _draft_helpers import D, P

LLM = "backend.draft_idea.llm_client.complete"


def _answer(scenes: int = 3, shots: int = 3, empty_first: bool = False) -> str:
    return json.dumps({
        "title": "Hydras Jahr", "logline": "Ein Wesen erlebt ein Jahr.",
        "elements": [{"key": "h", "kind": "character", "name": "Hydra", "description": "five heads"}],
        "scenes": [{"title": f"S{i}", "description": f"Beschreibung {i}", "element_keys": ["h"],
                    "shots": [] if (empty_first and i == 0) else
                    [{"shot": "wide", "prompt": f"prompt {i}.{j}", "element_keys": ["h"], "duration": 5} for j in range(shots)]}
                   for i in range(scenes)],
    })


def _idea(client, auth_headers, **body):
    with patch(LLM, new=AsyncMock(return_value=body.pop("_answer", _answer()))) as llm:
        r = client.post(f"{D}/idea", headers=auth_headers, json={"idea": "Hydra erlebt ein Jahr", "length": "30", **body})
    return r, llm


def test_one_shot_per_scene(client, auth_headers, ws) -> None:
    r, llm = _idea(client, auth_headers, shots_per_scene=1)
    assert r.status_code == 200, r.text
    scenes = r.json()["draft"]["scenes"]
    assert [len(s["shots"]) for s in scenes] == [1, 1, 1]
    assert [s["shots"][0]["prompt"] for s in scenes] == ["prompt 0.0", "prompt 1.0", "prompt 2.0"]      # der erste bleibt
    sys_prompt = llm.call_args.args[0][0]["content"]
    assert "exactly 1 shot" in sys_prompt and "2-5 shots" not in sys_prompt


def test_one_shot_fills_empty_scene(client, auth_headers, ws) -> None:
    r, _ = _idea(client, auth_headers, shots_per_scene=1, _answer=_answer(empty_first=True))
    first = r.json()["draft"]["scenes"][0]
    assert len(first["shots"]) == 1
    assert first["shots"][0]["prompt"] == "Beschreibung 0"                    # aus der Szenenbeschreibung
    assert first["shots"][0]["element_keys"] == ["h"]


def test_without_option_unchanged(client, auth_headers, ws) -> None:
    r, llm = _idea(client, auth_headers)
    assert [len(s["shots"]) for s in r.json()["draft"]["scenes"]] == [3, 3, 3]
    assert "2-5 shots" in llm.call_args.args[0][0]["content"]


def test_kind_goes_into_the_request(client, auth_headers, ws) -> None:
    for kind, word in (("trailer", "trailer"), ("explainer", "explainer"), ("short", "short film"), ("music", "music video")):
        _, llm = _idea(client, auth_headers, kind=kind)
        ctx = llm.call_args.args[0][1]["content"]
        assert f"Kind of film: {word}" in ctx, kind
    _, llm = _idea(client, auth_headers)
    assert "Kind of film" not in llm.call_args.args[0][1]["content"]


def test_bad_options(client, auth_headers) -> None:
    for extra in ({"kind": "doku"}, {"kind": 3}, {"shots_per_scene": 2}, {"shots_per_scene": True}, {"shots_per_scene": "1"}):
        r, llm = _idea(client, auth_headers, **extra)
        assert r.status_code == 400 and r.json()["detail"]["code"] == "studio_idea_invalid", extra
        assert not llm.called


def _apply(client, auth_headers, title: str, n: int, **extra):
    draft = {"head": {"title": title, "logline": f"{title} Logline", "description": "", "style": ""},
             "elements": [{"key": "h", "kind": "character", "name": "Hydra", "description": ""}],
             "scenes": [{"title": f"{title} {i}", "description": "", "element_keys": ["h"],
                         "shots": [{"shot": "", "prompt": "p", "element_keys": ["h"], "duration": 5}]} for i in range(n)]}
    return client.post(f"{D}/apply", headers=auth_headers, json={"draft": draft, **extra})


def test_replace_swaps_scenes_and_title(client, auth_headers, ws) -> None:
    assert _apply(client, auth_headers, "Alt", 3).status_code == 200
    plan = client.get(P, headers=auth_headers).json()
    old_ids = [s["id"] for s in plan["scenes"]]
    hydra = [e["id"] for e in plan["elements"]]
    r = _apply(client, auth_headers, "Neu", 2, replace=True)
    assert r.status_code == 200, r.text
    assert r.json()["mode"] == "replace" and r.json()["elements_reused"] == 1
    plan = client.get(P, headers=auth_headers).json()
    assert [s["title"] for s in plan["scenes"]] == ["Neu 0", "Neu 1"]
    assert not set(old_ids) & {s["id"] for s in plan["scenes"]}
    assert plan["screenplay"]["title"] == "Neu" and plan["screenplay"]["logline"] == "Neu Logline"     # überschrieben
    assert plan["screenplay"]["scene_order"] == [s["id"] for s in plan["scenes"]]
    assert [e["id"] for e in plan["elements"]] == hydra                                              # Figur bleibt
    for sid in old_ids:
        assert not (ws / "studio" / "scenes" / f"{sid}.json").exists()


def test_append_keeps_title(client, auth_headers, ws) -> None:
    _apply(client, auth_headers, "Alt", 1)
    r = _apply(client, auth_headers, "Neu", 1)
    assert r.json()["mode"] == "append"
    plan = client.get(P, headers=auth_headers).json()
    assert plan["screenplay"]["title"] == "Alt" and len(plan["scenes"]) == 2


def test_replace_with_bad_draft_deletes_nothing(client, auth_headers, ws) -> None:
    _apply(client, auth_headers, "Alt", 2)
    r = client.post(f"{D}/apply", headers=auth_headers, json={"draft": {"head": {}, "elements": [], "scenes": []}, "replace": True})
    assert r.status_code == 400 and r.json()["detail"]["code"] == "studio_draft_invalid"
    assert [s["title"] for s in client.get(P, headers=auth_headers).json()["scenes"]] == ["Alt 0", "Alt 1"]


def test_replace_only_with_true(client, auth_headers, ws) -> None:
    _apply(client, auth_headers, "Alt", 1)
    r = _apply(client, auth_headers, "Neu", 1, replace="yes")
    assert r.json()["mode"] == "append"
    assert len(client.get(P, headers=auth_headers).json()["scenes"]) == 2


def test_replace_into_empty_plan(client, auth_headers, ws) -> None:
    r = _apply(client, auth_headers, "Neu", 2, replace=True)
    assert r.status_code == 200 and r.json()["mode"] == "new"
