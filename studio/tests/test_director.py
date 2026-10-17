"""Studio 2b: Regie-Agent „In Shots zerlegen“ (studio/SPEC.md „Bauplan 2b“). Das LLM wird ersetzt."""
from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, patch

from conftest import MOD_PREFIX, PROJECT_ID

P = f"{MOD_PREFIX}/projects/{PROJECT_ID}/plan"
LLM = "backend.director.llm_client.complete"


def _setup(client, h) -> tuple[dict, dict, dict]:
    client.put(f"{P}/screenplay", headers=h, json={"look": {"style": "film noir"}, "models": {"text": "test/regie"}})
    mira = client.post(f"{P}/elements", headers=h, json={"kind": "character", "name": "Mira", "style_anchor": "red coat"}).json()
    ole = client.post(f"{P}/elements", headers=h, json={"kind": "character", "name": "Ole"}).json()
    sc = client.post(f"{P}/scenes", headers=h, json={
        "title": "Hafen", "description": "Mira wartet am Steg", "element_ids": [mira["id"]],
        "camera": {"light": "golden_hour"}, "dialogues": [{"element_id": mira["id"], "line": "Wo bist du?"}]}).json()
    return mira, ole, sc


def test_decompose_replaces_shots(client, auth_headers, ws) -> None:
    mira, ole, sc = _setup(client, auth_headers)
    D = f"{P}/scenes/{sc['id']}/decompose"
    client.post(f"{P}/scenes/{sc['id']}/shots", headers=auth_headers, json={"prompt": "alt"})
    answer = "```json\n" + json.dumps([
        {"shot": "wide", "prompt": "harbour at dawn", "element_ids": [mira["id"], ole["id"], "fremd"], "duration": 6},
        {"shot": "erfunden", "prompt": "her face", "element_ids": [mira["id"]], "duration": 99},
        {"prompt": "boat", "duration": 4}, {"prompt": "4"}, {"prompt": "5"}, {"prompt": "6"}, "kein Objekt"]) + "\n```"
    with patch(LLM, new=AsyncMock(return_value=answer)) as llm:
        r = client.post(D, headers=auth_headers, json={})
    assert r.status_code == 200, r.text
    shots = r.json()["shots"]
    assert r.json()["count"] == 5 and len(shots) == 5                      # höchstens 5
    assert [s["prompt"] for s in shots[:3]] == ["harbour at dawn", "her face", "boat"]
    assert shots[0]["element_ids"] == [mira["id"]]                          # nur Bausteine der Szene
    assert shots[1]["shot"] == "" and shots[1]["duration"] == 60
    assert all(s["status"] == "planned" and s["image_rel"] is None for s in shots)
    saved = client.get(P, headers=auth_headers).json()["scenes"][0]["shots"]
    assert [s["prompt"] for s in saved] == [s["prompt"] for s in shots]     # „alt“ ist ersetzt
    kwargs = llm.call_args.kwargs
    assert kwargs["model"] == "test/regie"                                  # Text-Modell aus dem Kopf
    ctx = "\n".join(m["content"] for m in llm.call_args.args[0])
    for needle in ("Mira wartet am Steg", "red coat", "film noir", "Wo bist du?", mira["id"], "golden hour", "closeup"):
        assert needle in ctx, needle
    assert ole["id"] not in ctx                                             # Baustein, der nicht in der Szene ist


def test_default_model_when_head_has_none(client, auth_headers, ws) -> None:
    sc = client.post(f"{P}/scenes", headers=auth_headers, json={"title": "S"}).json()
    with patch(LLM, new=AsyncMock(return_value='[{"prompt": "a"}]')) as llm:
        assert client.post(f"{P}/scenes/{sc['id']}/decompose", headers=auth_headers, json={}).status_code == 200
    assert llm.call_args.kwargs["model"] is None                            # Standard des Servers


def test_failure_keeps_old_shots(client, auth_headers, ws, caplog) -> None:
    _, _, sc = _setup(client, auth_headers)
    D = f"{P}/scenes/{sc['id']}/decompose"
    client.post(f"{P}/scenes/{sc['id']}/shots", headers=auth_headers, json={"prompt": "alt"})
    for side in ({"side_effect": RuntimeError("api down")}, {"return_value": "Leider nein."}, {"return_value": "[]"}):
        with patch(LLM, new=AsyncMock(**side)):
            r = client.post(D, headers=auth_headers, json={})
        assert r.status_code == 502 and r.json()["detail"]["code"] == "studio_decompose_failed", side
        assert [s["prompt"] for s in client.get(P, headers=auth_headers).json()["scenes"][0]["shots"]] == ["alt"]
    assert "LLM-Fehler" in caplog.text and "unbrauchbare Antwort" in caplog.text   # Ursache steht im Log


def test_shots_with_media_need_confirmation(client, auth_headers, ws) -> None:
    _, _, sc = _setup(client, auth_headers)
    D = f"{P}/scenes/{sc['id']}/decompose"
    client.put(f"{P}/scenes/{sc['id']}", headers=auth_headers, json={"shots": [{"prompt": "fertig", "image_rel": "atelier/images/a.png"}]})
    with patch(LLM, new=AsyncMock(return_value='[{"prompt": "neu"}]')) as llm:
        r = client.post(D, headers=auth_headers, json={})
        assert r.status_code == 409 and r.json()["detail"]["code"] == "studio_decompose_has_media"
        assert llm.call_count == 0                                          # kein LLM-Aufruf vor der Rückfrage
        for not_yes in ({"replace": "ja"}, {"replace": 1}, {"anders": True}):
            assert client.post(D, headers=auth_headers, json=not_yes).status_code == 409, not_yes
        assert client.post(D, headers=auth_headers, json={"replace": True}).status_code == 200
    assert [s["prompt"] for s in client.get(P, headers=auth_headers).json()["scenes"][0]["shots"]] == ["neu"]


def test_one_decompose_per_project(client, auth_headers, ws) -> None:
    from backend import director
    _, _, sc = _setup(client, auth_headers)

    async def run_twice():
        gate = asyncio.Event()

        async def slow(*a, **k):
            await gate.wait()
            return '[{"prompt": "a"}]'
        with patch(LLM, new=slow):
            first = asyncio.create_task(director.decompose(PROJECT_ID, sc["id"]))
            await asyncio.sleep(0)
            try:
                await director.decompose(PROJECT_ID, sc["id"])
                second = None
            except Exception as e:                                           # noqa: BLE001
                second = e
            gate.set()
            await first
            return second
    err = asyncio.run(run_twice())
    assert getattr(err, "code", None) == "studio_decompose_busy" and getattr(err, "status", None) == 409
    with patch(LLM, new=AsyncMock(return_value='[{"prompt": "b"}]')):     # danach wieder frei
        assert client.post(f"{P}/scenes/{sc['id']}/decompose", headers=auth_headers, json={}).status_code == 200


def test_unknown_scene(client, auth_headers, ws) -> None:
    with patch(LLM, new=AsyncMock(return_value='[{"prompt": "a"}]')) as llm:
        assert client.post(f"{P}/scenes/{'a' * 32}/decompose", headers=auth_headers, json={}).status_code == 404
    assert llm.call_count == 0
