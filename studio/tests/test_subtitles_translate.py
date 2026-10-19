"""Studio 6c: Untertitel übersetzen (Spec „Bauplan 6c“). Die Text-KI wird ersetzt."""
from __future__ import annotations

import json
import time
from unittest.mock import AsyncMock, patch

from _subtitle_helpers import P, S, cue, put
from _timeline_helpers import _code

LLM = "backend.subtitle_translate.llm_client.complete"
T = f"{S}/en/translate"


def _wait(client, h, timeout: float = 10.0) -> dict:
    end = time.time() + timeout
    while time.time() < end:
        jobs = [j for j in client.get(f"{P}/jobs", headers=h).json()["jobs"] if j["kind"] == "translate"]
        if jobs and jobs[0]["status"] in ("done", "failed", "cancelled"):
            return jobs[0]
        time.sleep(0.05)
    raise AssertionError("Übersetzen nicht fertig geworden")


def _answer(texts: list[str]) -> str:
    return "Hier die Übersetzung:\n```json\n" + json.dumps(texts, ensure_ascii=False) + "\n```"


def _de(client, h) -> list[dict]:
    cues = [cue(1, 0.5, 2, "Da ist er endlich."), cue(2, 2, 4.5, "Der alte Ole\nkommt nach Hause."), cue(3, 6, 8, "Ja.")]
    put(client, h, cues)
    return client.get(f"{S}/de", headers=h).json()["cues"]


def test_translate_keeps_times_and_order(client, auth_headers, ws) -> None:
    client.put(f"{P}/screenplay", headers=auth_headers, json={"models": {"text": "test/text"}, "title": "Nordwind", "logline": "Ole kehrt heim."})
    de = _de(client, auth_headers)
    with patch(LLM, new=AsyncMock(return_value=_answer(["There he is at last.", "Old Ole is coming home.", "Yes."]))) as llm:
        r = client.post(T, headers=auth_headers, json={"from": "de"})
        assert r.status_code == 202, r.text
        assert r.json()["kind"] == "translate"
        job = _wait(client, auth_headers)
    assert job["status"] == "done", job
    assert job["result"] == {"count": 3, "from": "de", "language": "en"}
    en = client.get(f"{S}/en", headers=auth_headers).json()
    assert en["source"] == "translation" and en["revision"] == 1 and en["from"] == "de"
    assert [(c["start"], c["end"]) for c in en["cues"]] == [(c["start"], c["end"]) for c in de]
    assert [c["text"] for c in en["cues"]] == ["There he is at last.", "Old Ole is coming home.", "Yes."]
    assert client.get(f"{S}/de", headers=auth_headers).json()["cues"] == de                # Original unverändert
    call = llm.call_args
    assert call.kwargs["model"] == "test/text"
    prompt = "\n".join(m["content"] for m in call.args[0])
    assert "English" in prompt and "German" in prompt and "Nordwind" in prompt and "Ole kehrt heim." in prompt
    assert "1. Da ist er endlich." in prompt and "2. Der alte Ole / kommt nach Hause." in prompt and "3. Ja." in prompt


def test_lines_are_wrapped_and_cut(client, auth_headers, ws) -> None:
    _de(client, auth_headers)
    long = "This is a much longer sentence than the original one and it has to be wrapped onto two lines for reading"
    with patch(LLM, new=AsyncMock(return_value=_answer([long, "x" * 400, "  Yes \n\n  indeed  "]))):
        client.post(T, headers=auth_headers, json={"from": "de"})
        assert _wait(client, auth_headers)["status"] == "done"
    cues = client.get(f"{S}/en", headers=auth_headers).json()["cues"]
    lines = cues[0]["text"].split("\n")
    assert len(lines) == 2 and " ".join(lines) == long and abs(len(lines[0]) - len(lines[1])) < 15   # kein Wort weg, ausgewogen
    assert len(cues[1]["text"]) <= 200 and cues[1]["text"].count("\n") <= 1
    short = "There he is at last."
    assert cues[2]["text"] == "Yes indeed"                                 # Umbruch neu gesetzt, nicht übernommen
    from backend.subtitle_translate import fit
    assert fit(short) == short and fit("a " * 30).count("\n") == 1 and all(len(x) <= 42 for x in fit("a " * 30).split("\n"))


def test_wrong_count_is_asked_again_once_then_fails(client, auth_headers, ws) -> None:
    _de(client, auth_headers)
    good = _answer(["A", "B", "C"])
    with patch(LLM, new=AsyncMock(side_effect=[_answer(["A", "B"]), good])) as llm:
        client.post(T, headers=auth_headers, json={"from": "de"})
        assert _wait(client, auth_headers)["status"] == "done"
    assert llm.await_count == 2
    with patch(LLM, new=AsyncMock(side_effect=["kein json", _answer(["A", "B", "C", "D"])])) as llm:
        client.post(T, headers=auth_headers, json={"from": "de", "replace": True})
        job = _wait(client, auth_headers)
    assert (job["status"], job["error"]) == ("failed", "bad_answer") and llm.await_count == 2
    assert [c["text"] for c in client.get(f"{S}/en", headers=auth_headers).json()["cues"]] == ["A", "B", "C"]   # alter Stand bleibt


def test_empty_or_non_text_entries_fail(client, auth_headers, ws) -> None:
    _de(client, auth_headers)
    with patch(LLM, new=AsyncMock(return_value=_answer(["A", "  ", "C"]))):
        client.post(T, headers=auth_headers, json={"from": "de"})
        assert _wait(client, auth_headers)["error"] == "bad_answer"
    with patch(LLM, new=AsyncMock(return_value=_answer(["A", 5, "C"]))):
        client.post(T, headers=auth_headers, json={"from": "de"})
        assert _wait(client, auth_headers)["error"] == "bad_answer"
    assert not (ws / "studio/subtitles/en.json").exists()


def test_big_lists_go_in_blocks(client, auth_headers, ws) -> None:
    put(client, auth_headers, [cue(i + 1, i, i + 0.6, f"Zeile {i}") for i in range(170)])
    seen = []

    async def fake(messages, **kw):
        lines = [x for x in messages[-1]["content"].splitlines() if x[:1].isdigit()]
        seen.append(len(lines))
        return _answer([f"Line {x.split('Zeile ', 1)[1]}" for x in lines])
    with patch(LLM, new=fake):
        client.post(T, headers=auth_headers, json={"from": "de"})
        assert _wait(client, auth_headers)["status"] == "done"
    assert seen == [80, 80, 10]
    cues = client.get(f"{S}/en", headers=auth_headers).json()["cues"]
    assert len(cues) == 170 and cues[169]["text"] == "Line 169" and cues[0]["text"] == "Line 0"


def test_rules(client, auth_headers, ws) -> None:
    assert _code(client.post(T, headers=auth_headers, json={"from": "de"})) == "400 studio_subtitles_empty"
    _de(client, auth_headers)
    assert _code(client.post(f"{S}/de/translate", headers=auth_headers, json={"from": "de"})) == "400 studio_subtitles_same_language"
    assert _code(client.post(f"{S}/xx/translate", headers=auth_headers, json={"from": "de"})) == "404 studio_not_found"
    assert _code(client.post(T, headers=auth_headers, json={"from": "xx"})) == "404 studio_not_found"
    assert _code(client.post(T, headers=auth_headers, json={})) == "404 studio_not_found"
    put(client, auth_headers, [cue(1, 0, 1, "Hello")], lang="en")
    assert _code(client.post(T, headers=auth_headers, json={"from": "de"})) == "409 studio_subtitles_not_empty"
    assert _code(client.post(T, headers=auth_headers, json={"from": "de", "replace": "ja"})) == "409 studio_subtitles_not_empty"


def test_provider_failure_and_change_meanwhile(client, auth_headers, ws) -> None:
    import asyncio
    _de(client, auth_headers)
    with patch(LLM, new=AsyncMock(side_effect=RuntimeError("weg"))):
        client.post(T, headers=auth_headers, json={"from": "de"})
        assert _wait(client, auth_headers)["error"] == "provider_failed"
    gate = {"open": False}

    async def slow(messages, **kw):
        for _ in range(100):
            if gate["open"]:
                break
            await asyncio.sleep(0.02)
        return _answer(["A", "B", "C"])
    with patch(LLM, new=slow):
        assert client.post(T, headers=auth_headers, json={"from": "de"}).status_code == 202
        assert _code(client.post(T, headers=auth_headers, json={"from": "de"})) == "409 studio_subtitles_running"
        put(client, auth_headers, [cue(1, 0, 1, "Inzwischen von Hand")], lang="en")
        gate["open"] = True
        job = _wait(client, auth_headers)
    assert (job["status"], job["error"]) == ("failed", "changed")
    assert client.get(f"{S}/en", headers=auth_headers).json()["cues"][0]["text"] == "Inzwischen von Hand"


def test_languages_list(client, auth_headers, ws) -> None:
    client.put(f"{P}/screenplay", headers=auth_headers, json={"language": "de"})
    assert client.get(f"{S.rsplit('/', 1)[0]}/subtitles", headers=auth_headers).json() == {"film": "de", "languages": [{"language": "de", "count": 0}]}
    put(client, auth_headers, [cue(1, 0, 1)], lang="fr")
    put(client, auth_headers, [cue(1, 0, 1), cue(2, 1, 2)], lang="en")
    out = client.get(f"{S.rsplit('/', 1)[0]}/subtitles", headers=auth_headers).json()
    assert out["languages"] == [{"language": "de", "count": 0}, {"language": "en", "count": 2}, {"language": "fr", "count": 1}]
    (ws / "studio/subtitles/kaputt.json").write_text("{}")
    (ws / "studio/subtitles/xx.json").write_text("{}")
    assert [x["language"] for x in client.get(f"{S.rsplit('/', 1)[0]}/subtitles", headers=auth_headers).json()["languages"]] == ["de", "en", "fr"]


def test_only_members(client, other_headers) -> None:
    assert client.post(T, headers=other_headers, json={"from": "de"}).status_code == 404
    assert client.get(f"{S.rsplit('/', 1)[0]}/subtitles", headers=other_headers).status_code == 404
