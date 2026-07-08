"""Atelier — Buddy-Lese-Tools (Ebene A): Kontext + Listen, keine Generierung."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from backend import characters, screenplay, tools_read
from conftest import PROJECT_ID


def _ctx(project_id=PROJECT_ID, user="testuser"):
    from hydrahive.tools.base import ToolContext
    return ToolContext(
        session_id="s", agent_id="a", user_id=user,
        workspace=Path("/tmp"), project_id=project_id,
    )


@pytest.mark.asyncio
async def test_projects_tool_lists_user_projects():
    tool = tools_read.PROJECTS_TOOL
    res = await tool.execute({}, _ctx())
    assert res.success
    ids = [p["id"] for p in res.output["projects"]]
    assert PROJECT_ID in ids
    assert res.output["active"] == PROJECT_ID


@pytest.mark.asyncio
async def test_models_tool_lists_by_category():
    tool = tools_read.MODELS_TOOL
    fake = [{"id": "google/veo-3.1", "name": "Veo 3.1"}, {"id": "a/b", "name": "B"}]
    with patch("backend.tools_read.list_video_models", new=AsyncMock(return_value=fake)):
        res = await tool.execute({"category": "video"}, _ctx())
    assert res.success
    # A–Z sortiert nach name
    names = [m["name"] for m in res.output["models"]]
    assert names == sorted(names, key=str.lower)
    assert res.output["category"] == "video"


@pytest.mark.asyncio
async def test_models_tool_rejects_unknown_category():
    res = await tools_read.MODELS_TOOL.execute({"category": "banana"}, _ctx())
    assert not res.success


@pytest.mark.asyncio
async def test_overview_tool_snapshots_project():
    characters.create_character(PROJECT_ID, {"name": "Held"})
    screenplay.create_scene(PROJECT_ID, {"title": "Szene 1"})
    res = await tools_read.OVERVIEW_TOOL.execute({}, _ctx())
    assert res.success
    o = res.output
    assert o["counts"]["characters"] >= 1
    assert o["counts"]["scenes"] >= 1
    assert "ci" in o and "screenplay" in o


@pytest.mark.asyncio
async def test_characters_tool_returns_profiles():
    characters.create_character(PROJECT_ID, {"name": "Figur X", "description": "desc"})
    res = await tools_read.CHARACTERS_TOOL.execute({}, _ctx())
    assert res.success
    names = [c["name"] for c in res.output["characters"]]
    assert "Figur X" in names


@pytest.mark.asyncio
async def test_read_tool_guards_foreign_project():
    # user 'other' darf nicht auf PROJECT_ID (gehört 'testuser')
    res = await tools_read.OVERVIEW_TOOL.execute({}, _ctx(user="other"))
    assert not res.success


@pytest.mark.asyncio
async def test_read_tool_needs_project():
    res = await tools_read.OVERVIEW_TOOL.execute({}, _ctx(project_id=None))
    assert not res.success
