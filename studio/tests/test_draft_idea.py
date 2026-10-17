"""Studio B2: Entwurf aus einer Idee (studio/SPEC.md „Bauplan B2“). Das LLM wird ersetzt; nichts wird gespeichert."""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

from _draft_helpers import D, P
from conftest import MOD_PREFIX, OTHER_PROJECT_ID

LLM = "backend.draft_idea.llm_client.complete"


def _answer(scenes: int = 3, shots: int = 3) -> str:
    return "Hier ist dein Film:\n```json\n" + json.dumps({
        "title": "Licht im Sturm", "logline": "Eine Wärterin hält das Licht.",
        "elements": [{"key": "mira", "kind": "character", "name": "Mira", "description": "red coat"},
                     {"key": "turm", "kind": "place", "name": "Leuchtturm", "description": "white tower"},
                     {"key": "x", "kind": "vehicle", "name": "Auto"}],
        "scenes": [{"title": f"S{i}", "description": f"Beschreibung {i}", "location": "Klippe", "time_of_day": "Nacht",
                    "element_keys": ["mira", "turm", "unbekannt"],
                    "shots": [{"shot": "wide" if j == 0 else "erfunden", "prompt": f"shot {i}.{j}", "element_keys": ["mira"],
                               "duration": 99 if j == 1 else 4} for j in range(shots)]} for i in range(scenes)],
    }) + "\n```"


def test_idea_gives_a_draft_and_saves_nothing(client, auth_headers, ws) -> None:
    client.put(f"{P}/screenplay", headers=auth_headers, json={"models": {"text": "test/idee"}})
    before = sorted(p.name for p in (ws / "studio").rglob("*"))
    with patch(LLM, new=AsyncMock(return_value=_answer())) as llm:
        r = client.post(f"{D}/idea", headers=auth_headers, json={"idea": "Ein Leuchtturm im Sturm", "length": "60", "style": "Noir"})
    assert r.status_code == 200, r.text
    d = r.json()["draft"]
    assert d["head"]["title"] == "Licht im Sturm" and d["head"]["logline"] == "Eine Wärterin hält das Licht."
    assert d["head"]["style"] == "Noir"
    assert [e["kind"] for e in d["elements"]] == ["character", "place"]               # unbekannte Art fällt weg
    assert len(d["scenes"]) == 3
    sc = d["scenes"][0]
    assert sc["element_keys"] == ["mira", "turm"] and sc["location"] == "Klippe"     # unbekannter Schlüssel fällt weg
    assert [s["shot"] for s in sc["shots"]] == ["wide", "", ""]                      # unbekannte Einstellung → leer
    assert [s["duration"] for s in sc["shots"]] == [4, 10, 4]                        # 3–10 s
    assert sorted(p.name for p in (ws / "studio").rglob("*")) == before              # nichts geschrieben
    kwargs = llm.call_args.kwargs
    assert kwargs["model"] == "test/idee"
    ctx = "\n".join(m["content"] for m in llm.call_args.args[0])
    for needle in ("Ein Leuchtturm im Sturm", "Noir", "60", "closeup"):
        assert needle in ctx, needle


def test_limits_scenes_and_shots(client, auth_headers, ws) -> None:
    with patch(LLM, new=AsyncMock(return_value=_answer(scenes=12, shots=9))):
        d = client.post(f"{D}/idea", headers=auth_headers, json={"idea": "x", "length": "30"}).json()["draft"]
    assert len(d["scenes"]) == 8 and all(len(s["shots"]) == 5 for s in d["scenes"])


def test_bad_input(client, auth_headers) -> None:
    for body in ({"idea": "", "length": "30"}, {"idea": "x" * 2001, "length": "30"}, {"idea": "x", "length": "45"},
                 {"idea": "x", "length": "30", "style": "s" * 301}):
        r = client.post(f"{D}/idea", headers=auth_headers, json=body)
        assert r.status_code == 400 and r.json()["detail"]["code"] == "studio_idea_invalid", body


def test_unusable_answer_or_llm_error(client, auth_headers, ws) -> None:
    for mock in (AsyncMock(return_value="leider nein"), AsyncMock(return_value='{"scenes": []}'),
                 AsyncMock(side_effect=RuntimeError("down"))):
        with patch(LLM, new=mock):
            r = client.post(f"{D}/idea", headers=auth_headers, json={"idea": "x", "length": "30"})
        assert r.status_code == 502 and r.json()["detail"]["code"] == "studio_idea_failed"
    assert not (ws / "studio" / "scenes").exists()


def test_foreign_project(client, auth_headers) -> None:
    r = client.post(f"{MOD_PREFIX}/projects/{OTHER_PROJECT_ID}/plan/draft/idea", headers=auth_headers, json={"idea": "x", "length": "30"})
    assert r.status_code == 404
