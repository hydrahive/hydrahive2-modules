"""Atelier — Regie E4: Shot-Storage/CRUD + LLM-Zerlegung (gemockt)."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from backend import director, screenplay
from conftest import PROJECT_ID


# ---------------------------------------------------------------- Task 1: Shot-Storage/CRUD
def test_get_shots_leer():
    s = screenplay.create_scene(PROJECT_ID, {"title": "S"})
    assert director.get_shots(PROJECT_ID, s["id"]) == []


def test_get_shots_ungueltige_id():
    assert director.get_shots(PROJECT_ID, "keine-hex") == []


def test_save_und_get_shots_sanitized():
    s = screenplay.create_scene(PROJECT_ID, {"title": "S"})
    saved = director.save_shots(PROJECT_ID, s["id"], [
        {"shot": "wide", "prompt": "a knight", "duration": 999, "status": "quatsch"},
        {"shot": "closeup", "prompt": "his face"},
    ])
    assert len(saved) == 2
    assert saved[0]["order"] == 0 and saved[1]["order"] == 1
    assert saved[0]["duration"] == 60          # auf max geklemmt
    assert saved[0]["status"] == "planned"     # ungültiger Status → planned
    got = director.get_shots(PROJECT_ID, s["id"])
    assert [x["prompt"] for x in got] == ["a knight", "his face"]


def test_update_shot():
    s = screenplay.create_scene(PROJECT_ID, {"title": "S"})
    saved = director.save_shots(PROJECT_ID, s["id"], [{"shot": "wide", "prompt": "alt"}])
    sid = saved[0]["id"]
    upd = director.update_shot(PROJECT_ID, s["id"], sid, {"prompt": "neu"})
    assert upd["prompt"] == "neu"
    assert director.get_shots(PROJECT_ID, s["id"])[0]["prompt"] == "neu"


def test_update_shot_unbekannt():
    s = screenplay.create_scene(PROJECT_ID, {"title": "S"})
    director.save_shots(PROJECT_ID, s["id"], [{"shot": "wide", "prompt": "x"}])
    assert director.update_shot(PROJECT_ID, s["id"], "gibtsnicht", {"prompt": "y"}) is None


def test_delete_shot():
    s = screenplay.create_scene(PROJECT_ID, {"title": "S"})
    saved = director.save_shots(PROJECT_ID, s["id"], [
        {"shot": "wide", "prompt": "a"}, {"shot": "closeup", "prompt": "b"},
    ])
    assert director.delete_shot(PROJECT_ID, s["id"], saved[0]["id"]) is True
    rest = director.get_shots(PROJECT_ID, s["id"])
    assert len(rest) == 1 and rest[0]["prompt"] == "b"
    assert director.delete_shot(PROJECT_ID, s["id"], "gibtsnicht") is False


# ---------------------------------------------------------------- Task 2: JSON-Parsing
def test_parse_shots_plain():
    raw = '[{"shot":"wide","prompt":"p","duration":5}]'
    assert director._parse_shots_json(raw)[0]["shot"] == "wide"


def test_parse_shots_mit_fences_und_text():
    raw = 'Sure!\n```json\n[{"shot":"closeup","prompt":"p"}]\n```\nDone.'
    out = director._parse_shots_json(raw)
    assert len(out) == 1 and out[0]["shot"] == "closeup"


def test_parse_shots_kaputt():
    assert director._parse_shots_json("kein json") == []
    assert director._parse_shots_json("") == []


# ---------------------------------------------------------------- Task 2: decompose (LLM gemockt)
@pytest.mark.asyncio
async def test_decompose_scene_erzeugt_planned_shots():
    s = screenplay.create_scene(PROJECT_ID, {
        "title": "Ruinentor", "description": "Ritter tritt ein",
        "character_ids": ["a" * 32],
    })
    fake = '[{"shot":"wide","prompt":"knight at gate","character_ids":["a'+ "a"*31 + '","fremd"],"duration":6},' \
           '{"shot":"closeup","prompt":"his eyes","character_ids":[],"duration":4}]'
    with patch("backend.director.llm_client.complete", new=AsyncMock(return_value=fake)):
        shots = await director.decompose_scene(PROJECT_ID, s)
    assert len(shots) == 2
    assert all(sh["status"] == "planned" for sh in shots)
    # fremde Charakter-ID wurde herausgefiltert (nur Szenen-Charaktere erlaubt)
    assert shots[0]["character_ids"] == ["a" * 32]
    # persistiert
    assert len(director.get_shots(PROJECT_ID, s["id"])) == 2


@pytest.mark.asyncio
async def test_decompose_scene_llm_fehler_leer():
    s = screenplay.create_scene(PROJECT_ID, {"title": "S"})
    with patch("backend.director.llm_client.complete", new=AsyncMock(side_effect=RuntimeError("api down"))):
        shots = await director.decompose_scene(PROJECT_ID, s)
    assert shots == []


@pytest.mark.asyncio
async def test_decompose_all_zaehlt_zusammen():
    a = screenplay.create_scene(PROJECT_ID, {"title": "A"})
    screenplay.create_scene(PROJECT_ID, {"title": "B"})
    fake = '[{"shot":"wide","prompt":"x","duration":5}]'
    with patch("backend.director.llm_client.complete", new=AsyncMock(return_value=fake)):
        summary = await director.decompose_all(PROJECT_ID)
    assert summary["scenes"] == 2
    assert summary["shots"] == 2
    assert summary["per_scene"][a["id"]] == 1


# ---------------------------------------------------------------- Task 3: Routen
PREFIX = f"/api/modules/atelier/projects/{PROJECT_ID}"
from conftest import OTHER_PROJECT_ID  # noqa: E402
OTHER_PREFIX = f"/api/modules/atelier/projects/{OTHER_PROJECT_ID}"


def test_decompose_route_guard(client, auth_headers):
    r = client.post(f"{OTHER_PREFIX}/screenplay/decompose", json={}, headers=auth_headers)
    assert r.status_code == 404


def test_decompose_route_braucht_auth(client):
    assert client.post(f"{PREFIX}/screenplay/decompose", json={}).status_code == 401


def test_decompose_route_erzeugt_shots(client, auth_headers):
    screenplay.create_scene(PROJECT_ID, {"title": "Route-Szene", "description": "x"})
    fake = '[{"shot":"wide","prompt":"a shot","duration":5}]'
    with patch("backend.director.llm_client.complete", new=AsyncMock(return_value=fake)):
        r = client.post(f"{PREFIX}/screenplay/decompose", json={}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["shots"] >= 1


def test_shot_crud_routes(client, auth_headers):
    s = screenplay.create_scene(PROJECT_ID, {"title": "CRUD"})
    director.save_shots(PROJECT_ID, s["id"], [{"shot": "wide", "prompt": "orig"}])
    sid = s["id"]
    lst = client.get(f"{PREFIX}/screenplay/scenes/{sid}/shots", headers=auth_headers).json()
    assert len(lst) == 1
    shot_id = lst[0]["id"]
    upd = client.put(f"{PREFIX}/screenplay/scenes/{sid}/shots/{shot_id}",
                     json={"shot": "closeup", "prompt": "edited", "duration": 4},
                     headers=auth_headers)
    assert upd.status_code == 200 and upd.json()["prompt"] == "edited"
    dele = client.delete(f"{PREFIX}/screenplay/scenes/{sid}/shots/{shot_id}", headers=auth_headers)
    assert dele.status_code == 200
    assert client.get(f"{PREFIX}/screenplay/scenes/{sid}/shots", headers=auth_headers).json() == []


def test_update_shot_route_404(client, auth_headers):
    s = screenplay.create_scene(PROJECT_ID, {"title": "x"})
    r = client.put(f"{PREFIX}/screenplay/scenes/{s['id']}/shots/gibtsnicht",
                   json={"prompt": "y"}, headers=auth_headers)
    assert r.status_code == 404


# ---------------------------------------------------------------- E5: Batch-Render
@pytest.mark.asyncio
async def test_render_all_erzeugt_clips_und_film():
    a = screenplay.create_scene(PROJECT_ID, {"title": "A"})
    director.save_shots(PROJECT_ID, a["id"], [
        {"shot": "wide", "prompt": "p1", "duration": 5},
        {"shot": "closeup", "prompt": "p2", "duration": 4},
    ])
    with (
        patch("backend.director.service.generate_for_project",
              side_effect=lambda pid, req: {"rel": "output/key.png"}),
        patch("backend.director.video.render_clip",
              new=AsyncMock(side_effect=["videos/c1.mp4", "videos/c2.mp4"])),
        patch("backend.director._director_mux.mux_screenplay_film",
              new=AsyncMock(return_value="films/final.mp4")),
    ):
        job = await director.render_all(PROJECT_ID)
    assert job["total_shots"] == 2
    assert job["done_shots"] == 2
    assert job["failed_shots"] == 0
    assert job["film_rel"] == "films/final.mp4"
    # Shots sind jetzt done, mit video_rel
    shots = director.get_shots(PROJECT_ID, a["id"])
    assert all(s["status"] == "done" for s in shots)
    assert shots[0]["video_rel"] == "videos/c1.mp4"


@pytest.mark.asyncio
async def test_render_all_shot_fehler_bricht_nicht_ab():
    a = screenplay.create_scene(PROJECT_ID, {"title": "A"})
    director.save_shots(PROJECT_ID, a["id"], [
        {"shot": "wide", "prompt": "ok"},
        {"shot": "closeup", "prompt": "boom"},
    ])
    with (
        patch("backend.director.service.generate_for_project",
              side_effect=lambda pid, req: {"rel": "output/key.png"}),
        patch("backend.director.video.render_clip",
              new=AsyncMock(side_effect=["videos/ok.mp4", RuntimeError("clip failed")])),
        patch("backend.director._director_mux.mux_screenplay_film",
              new=AsyncMock(return_value="films/final.mp4")),
    ):
        job = await director.render_all(PROJECT_ID)
    assert job["done_shots"] == 1
    assert job["failed_shots"] == 1
    assert job["status"] == "completed_with_errors"
    shots = director.get_shots(PROJECT_ID, a["id"])
    assert shots[0]["status"] == "done"
    assert shots[1]["status"] == "failed"


@pytest.mark.asyncio
async def test_render_all_keine_shots_kein_film():
    screenplay.create_scene(PROJECT_ID, {"title": "leer"})
    with patch("backend.director._director_mux.mux_screenplay_film", new=AsyncMock()) as film_mock:
        job = await director.render_all(PROJECT_ID)
    assert job["total_shots"] == 0
    assert job["film_rel"] is None
    film_mock.assert_not_called()


def test_get_render_job_default_idle():
    # frisches Projekt (conftest räumt Atelier-Dirs) → idle
    assert director.get_render_job(PROJECT_ID)["status"] in ("idle", "processing", "completed", "completed_with_errors")


# ---------------------------------------------------------------- E5: Render-Routen
def test_render_route_guard(client, auth_headers):
    assert client.post(f"{OTHER_PREFIX}/screenplay/render", json={}, headers=auth_headers).status_code == 404


def test_render_route_braucht_auth(client):
    assert client.post(f"{PREFIX}/screenplay/render", json={}).status_code == 401


def test_render_status_route(client, auth_headers):
    r = client.get(f"{PREFIX}/screenplay/render", headers=auth_headers)
    assert r.status_code == 200
    assert "status" in r.json()


def test_render_route_startet(client, auth_headers):
    # render_all wird gemockt, damit kein echter Task läuft
    with patch("backend.director.render_all", new=AsyncMock(return_value={"status": "completed"})):
        r = client.post(f"{PREFIX}/screenplay/render", json={}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "started"
