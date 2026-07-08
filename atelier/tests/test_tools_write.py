"""Atelier — Buddy-Anlege-Tools (Ebene B): voreinstellen, nichts generieren."""
from __future__ import annotations

from pathlib import Path

import pytest

from backend import characters, screenplay, tools_write
from conftest import PROJECT_ID


def _ctx(project_id=PROJECT_ID, user="testuser"):
    from hydrahive.tools.base import ToolContext
    return ToolContext(
        session_id="s", agent_id="a", user_id=user,
        workspace=Path("/tmp"), project_id=project_id,
    )


@pytest.mark.asyncio
async def test_set_ci_persists():
    res = await tools_write.SET_CI_TOOL.execute(
        {"style_anchor": "noir, high contrast", "default_model": "google/gemini-2.5-flash-image",
         "aspect_ratio": "16:9", "palette": ["#111", "#eee"]}, _ctx())
    assert res.success
    ci = characters.get_ci(PROJECT_ID)
    assert ci["style_anchor"] == "noir, high contrast"
    assert ci["default_model"] == "google/gemini-2.5-flash-image"
    assert ci["aspect_ratio"] == "16:9"


@pytest.mark.asyncio
async def test_character_create_update_delete():
    # create
    res = await tools_write.CHARACTER_TOOL.execute(
        {"action": "create", "name": "Aria", "description": "Elfen-Magierin"}, _ctx())
    assert res.success
    cid = res.output["character"]["id"]
    assert res.output["character"]["name"] == "Aria"

    # update
    res = await tools_write.CHARACTER_TOOL.execute(
        {"action": "update", "character_id": cid, "seed": 42}, _ctx())
    assert res.success
    assert res.output["character"]["seed"] == 42

    # delete
    res = await tools_write.CHARACTER_TOOL.execute(
        {"action": "delete", "character_id": cid}, _ctx())
    assert res.success
    assert characters.get_character(PROJECT_ID, cid) is None


@pytest.mark.asyncio
async def test_character_update_missing_id_fails():
    res = await tools_write.CHARACTER_TOOL.execute({"action": "update", "name": "x"}, _ctx())
    assert not res.success


@pytest.mark.asyncio
async def test_character_unknown_action_fails():
    res = await tools_write.CHARACTER_TOOL.execute({"action": "frobnicate"}, _ctx())
    assert not res.success


@pytest.mark.asyncio
async def test_scene_create_update_reorder_delete():
    r1 = await tools_write.SCENE_TOOL.execute(
        {"action": "create", "title": "Szene A", "description": "Ankunft"}, _ctx())
    r2 = await tools_write.SCENE_TOOL.execute(
        {"action": "create", "title": "Szene B"}, _ctx())
    assert r1.success and r2.success
    id1 = r1.output["scene"]["id"]
    id2 = r2.output["scene"]["id"]

    # reorder
    res = await tools_write.SCENE_TOOL.execute(
        {"action": "reorder", "scene_ids": [id2, id1]}, _ctx())
    assert res.success

    # update
    res = await tools_write.SCENE_TOOL.execute(
        {"action": "update", "scene_id": id1, "location": "Wald"}, _ctx())
    assert res.success
    assert res.output["scene"]["location"] == "Wald"

    # delete
    res = await tools_write.SCENE_TOOL.execute(
        {"action": "delete", "scene_id": id2}, _ctx())
    assert res.success
    remaining = [s["id"] for s in screenplay.list_scenes(PROJECT_ID)]
    assert id2 not in remaining


@pytest.mark.asyncio
async def test_set_screenplay_head():
    res = await tools_write.SCREENPLAY_TOOL.execute(
        {"title": "Mein Film", "film_model": "google/veo-3.1", "aspect_ratio": "21:9"}, _ctx())
    assert res.success
    head = screenplay.get_screenplay(PROJECT_ID)
    assert head["title"] == "Mein Film"
    assert head["film_model"] == "google/veo-3.1"


@pytest.mark.asyncio
async def test_write_tool_guards_foreign_project():
    res = await tools_write.CHARACTER_TOOL.execute(
        {"action": "create", "name": "X"}, _ctx(user="other"))
    assert not res.success


@pytest.mark.asyncio
async def test_write_tool_needs_project():
    res = await tools_write.SET_CI_TOOL.execute({"style_anchor": "x"}, _ctx(project_id=None))
    assert not res.success
