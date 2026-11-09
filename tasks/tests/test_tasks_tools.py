"""Unit-Tests für die Agent-Tools des Tasks-Moduls."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from hydrahive.db import init_db
from hydrahive.tools.base import ToolContext


def make_ctx(username: str = "alice", session_id: str = "sess-1") -> ToolContext:
    return ToolContext(
        session_id=session_id,
        agent_id="agent-1",
        user_id=username,
        workspace=Path("/tmp"),
    )


@pytest.fixture(autouse=True)
def fresh_db():
    from _hh_isolation import only_own_rows
    init_db()
    with only_own_rows("module_tasks"):
        yield


# ── task_write ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_task_write_creates_task():
    from backend.tools.task_write import TOOL
    result = await TOOL.execute({"title": "Testen", "priority": "high"}, make_ctx())
    assert result.success
    assert result.output["created"] is True
    assert result.output["task"]["title"] == "Testen"
    assert result.output["task"]["priority"] == "high"
    assert result.output["task"]["status"] == "open"


@pytest.mark.asyncio
async def test_task_write_updates_existing():
    from backend.tools.task_write import TOOL
    r1 = await TOOL.execute({"title": "Initial"}, make_ctx())
    task_id = r1.output["task"]["id"]

    r2 = await TOOL.execute({"task_id": task_id, "status": "done", "title": "Erledigt"}, make_ctx())
    assert r2.success
    assert r2.output["updated"] is True
    assert r2.output["task"]["status"] == "done"
    assert r2.output["task"]["title"] == "Erledigt"


@pytest.mark.asyncio
async def test_task_write_invalid_task_id():
    from backend.tools.task_write import TOOL
    r = await TOOL.execute({"task_id": "nonexistent", "title": "X"}, make_ctx())
    assert not r.success


@pytest.mark.asyncio
async def test_task_write_inherits_project_from_ctx():
    from backend.tools.task_write import TOOL
    ctx = make_ctx()
    ctx.project_id = "my-project"
    r = await TOOL.execute({"title": "Mit Projekt"}, ctx)
    assert r.output["task"]["project_id"] == "my-project"


# ── task_list ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_task_list_empty():
    from backend.tools.task_list import TOOL
    r = await TOOL.execute({}, make_ctx())
    assert r.success
    assert r.output["count"] == 0


@pytest.mark.asyncio
async def test_task_list_returns_created_tasks():
    from backend.tools.task_write import TOOL as write
    from backend.tools.task_list import TOOL as lst
    ctx = make_ctx()
    await write.execute({"title": "Eins"}, ctx)
    await write.execute({"title": "Zwei"}, ctx)

    r = await lst.execute({}, ctx)
    assert r.output["count"] == 2
    titles = [t["title"] for t in r.output["tasks"]]
    assert "Eins" in titles
    assert "Zwei" in titles


@pytest.mark.asyncio
async def test_task_list_filter_by_status():
    from backend.tools.task_write import TOOL as write
    from backend.tools.task_list import TOOL as lst
    ctx = make_ctx()
    r = await write.execute({"title": "Offen"}, ctx)
    task_id = r.output["task"]["id"]
    await write.execute({"task_id": task_id, "status": "done"}, ctx)
    await write.execute({"title": "Noch offen"}, ctx)

    r = await lst.execute({"status": "open"}, ctx)
    assert r.output["count"] == 1
    assert r.output["tasks"][0]["title"] == "Noch offen"


@pytest.mark.asyncio
async def test_task_list_user_isolation():
    from backend.tools.task_write import TOOL as write
    from backend.tools.task_list import TOOL as lst
    await write.execute({"title": "Alices Task"}, make_ctx("alice"))
    await write.execute({"title": "Bobs Task"},   make_ctx("bob"))

    alice_result = await lst.execute({}, make_ctx("alice"))
    assert alice_result.output["count"] == 1
    assert alice_result.output["tasks"][0]["title"] == "Alices Task"


@pytest.mark.asyncio
async def test_task_list_paginates_compact_results_with_bounded_output():
    from backend.tools.task_list import TOOL as lst
    from backend.tools.task_write import TOOL as write

    ctx = make_ctx()
    for index in range(25):
        await write.execute(
            {"title": f"Task {index:02d}", "description": f"Beschreibung {index}: " + "x" * 10_000},
            ctx,
        )

    first = await lst.execute({}, ctx)
    assert first.success
    assert first.output["count"] == 25
    assert first.output["returned"] == 20
    assert first.output["limit"] == 20
    assert first.output["offset"] == 0
    assert first.output["has_more"] is True
    assert first.output["next_offset"] == 20
    assert first.output["budget_limited"] is False
    assert all("description" not in task for task in first.output["tasks"])
    assert all(len(task["description_preview"]) <= 80 for task in first.output["tasks"])
    assert len(json.dumps(first.output, ensure_ascii=False)) < 15_000

    second = await lst.execute({"limit": 10, "offset": 20}, ctx)
    assert second.output["count"] == 25
    assert second.output["returned"] == 5
    assert second.output["has_more"] is False
    assert second.output["next_offset"] is None
    first_ids = {task["id"] for task in first.output["tasks"]}
    second_ids = {task["id"] for task in second.output["tasks"]}
    assert first_ids.isdisjoint(second_ids)
    assert len(first_ids | second_ids) == 25


@pytest.mark.asyncio
async def test_task_list_shortens_page_to_hard_output_budget():
    from backend.tools.task_list import TOOL as lst
    from backend.tools.task_write import TOOL as write

    ctx = make_ctx()
    for index in range(100):
        await write.execute(
            {"title": f"{index:03d}-" + "T" * 495, "description": "D" * 10_000},
            ctx,
        )

    result = await lst.execute({"limit": 100}, ctx)
    serialized = json.dumps(result.output, ensure_ascii=False)
    assert result.output["count"] == 100
    assert result.output["budget_limited"] is True
    assert 0 < result.output["returned"] < 100
    assert result.output["next_offset"] == result.output["returned"]
    assert len(serialized) <= 40_000


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "args",
    [
        {"limit": 0},
        {"limit": 101},
        {"limit": True},
        {"offset": -1},
        {"offset": False},
    ],
)
async def test_task_list_rejects_invalid_pagination(args):
    from backend.tools.task_list import TOOL

    result = await TOOL.execute(args, make_ctx())
    assert not result.success
    assert "Pagination" in result.error


@pytest.mark.asyncio
async def test_task_list_project_filter_applies_to_page_and_total():
    from backend.tools.task_list import TOOL as lst
    from backend.tools.task_write import TOOL as write

    ctx = make_ctx()
    await write.execute({"title": "Projekt A", "project_id": "a"}, ctx)
    await write.execute({"title": "Projekt B", "project_id": "b"}, ctx)

    result = await lst.execute({"project_id": "a"}, ctx)
    assert result.output["count"] == 1
    assert result.output["returned"] == 1
    assert result.output["tasks"][0]["project_id"] == "a"


# ── task_read ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_task_read_by_full_id():
    from backend.tools.task_write import TOOL as write
    from backend.tools.task_read import TOOL as read
    ctx = make_ctx()
    r = await write.execute({"title": "Lesbar", "description": "Wichtig"}, ctx)
    task_id = r.output["task"]["id"]

    r2 = await read.execute({"task_id": task_id}, ctx)
    assert r2.success
    assert r2.output["task"]["title"] == "Lesbar"
    assert r2.output["task"]["description"] == "Wichtig"


@pytest.mark.asyncio
async def test_task_read_by_prefix():
    from backend.tools.task_write import TOOL as write
    from backend.tools.task_read import TOOL as read
    ctx = make_ctx()
    r = await write.execute({"title": "Prefix-Test"}, ctx)
    prefix = r.output["task"]["id"][:8]

    r2 = await read.execute({"task_id": prefix}, ctx)
    assert r2.success
    assert r2.output["task"]["title"] == "Prefix-Test"


@pytest.mark.asyncio
async def test_task_read_not_found():
    from backend.tools.task_read import TOOL as read
    r = await read.execute({"task_id": "doesnotexist"}, make_ctx())
    assert not r.success


@pytest.mark.asyncio
async def test_task_read_user_isolation():
    from backend.tools.task_write import TOOL as write
    from backend.tools.task_read import TOOL as read
    r = await write.execute({"title": "Geheim"}, make_ctx("alice"))
    task_id = r.output["task"]["id"]

    r2 = await read.execute({"task_id": task_id}, make_ctx("bob"))
    assert not r2.success


# ── Kurz-ID in allen drei Tools gleich (Task d61ae32b) ───────────────────────

@pytest.mark.asyncio
async def test_task_write_updates_by_prefix():
    from backend.tools.task_write import TOOL as write
    ctx = make_ctx()
    r = await write.execute({"title": "Kurz"}, ctx)
    full = r.output["task"]["id"]

    r2 = await write.execute({"task_id": full[:8], "title": "Kurz", "status": "done"}, ctx)
    assert r2.success, r2.error
    assert r2.output["task"]["id"] == full
    assert r2.output["task"]["status"] == "done"


@pytest.mark.asyncio
async def test_task_write_prefix_note_appends():
    from backend.tools.task_write import TOOL as write
    ctx = make_ctx()
    r = await write.execute({"title": "Mit Notiz", "description": "Start"}, ctx)
    full = r.output["task"]["id"]

    r2 = await write.execute({"task_id": full[:8], "title": "Mit Notiz", "note": "weiter"}, ctx)
    assert r2.success, r2.error
    desc = r2.output["task"]["description"]
    assert desc.startswith("Start\n\n[") and desc.endswith("] weiter")


@pytest.mark.asyncio
async def test_task_write_prefix_ambiguous_changes_nothing(monkeypatch):
    from backend import service
    from backend.tools.task_write import TOOL as write
    ctx = make_ctx()
    ids = iter(["abcd1234-0000-4000-8000-000000000001", "abcd1234-0000-4000-8000-000000000002"])
    monkeypatch.setattr(service.uuid, "uuid4", lambda: next(ids))
    await write.execute({"title": "Eins"}, ctx)
    await write.execute({"title": "Zwei"}, ctx)

    r = await write.execute({"task_id": "abcd1234", "title": "X", "status": "done"}, ctx)
    assert not r.success
    assert "Mehrdeutig" in r.error and "abcd1234" in r.error
    titles = {t["title"] for t in service.list_tasks("alice")}
    assert titles == {"Eins", "Zwei"}


@pytest.mark.asyncio
async def test_task_write_prefix_foreign_task_not_found():
    from backend import service
    from backend.tools.task_write import TOOL as write
    r = await write.execute({"title": "Von Bob"}, make_ctx("bob"))
    bob_id = r.output["task"]["id"]

    r2 = await write.execute({"task_id": bob_id[:8], "title": "Übernommen"}, make_ctx("alice"))
    assert not r2.success
    assert service.get_task("bob", bob_id)["title"] == "Von Bob"


@pytest.mark.asyncio
@pytest.mark.parametrize("tool", ["task_read", "task_delete"])
@pytest.mark.parametrize("bad", ["", "   "])
async def test_blank_id_never_matches_a_task(tool, bad):
    """Leere ID darf nicht per startswith("") den einzigen Task treffen."""
    import importlib

    from backend import service
    from backend.tools.task_write import TOOL as write
    ctx = make_ctx()
    r = await write.execute({"title": "Einziger Task"}, ctx)
    only = r.output["task"]["id"]

    mod = importlib.import_module(f"backend.tools.{tool}")
    r2 = await mod.TOOL.execute({"task_id": bad}, ctx)
    assert not r2.success
    assert service.get_task("alice", only) is not None


@pytest.mark.asyncio
async def test_task_delete_by_prefix_still_works():
    from backend import service
    from backend.tools.task_delete import TOOL as delete
    from backend.tools.task_write import TOOL as write
    ctx = make_ctx()
    r = await write.execute({"title": "Weg damit"}, ctx)
    full = r.output["task"]["id"]

    r2 = await delete.execute({"task_id": full[:8]}, ctx)
    assert r2.success
    assert r2.output["task_id"] == full
    assert service.get_task("alice", full) is None


@pytest.mark.asyncio
@pytest.mark.parametrize("tool", ["task_read", "task_delete", "task_write"])
async def test_prefix_with_spaces_resolves(tool):
    import importlib

    from backend.tools.task_write import TOOL as write
    ctx = make_ctx()
    r = await write.execute({"title": "Mit Leerzeichen"}, ctx)
    full = r.output["task"]["id"]

    args = {"task_id": f"  {full[:8]}  "}
    if tool == "task_write":
        args["title"] = "Mit Leerzeichen"
    mod = importlib.import_module(f"backend.tools.{tool}")
    r2 = await mod.TOOL.execute(args, ctx)
    assert r2.success, r2.error


@pytest.mark.asyncio
@pytest.mark.parametrize("tool", ["task_read", "task_delete"])
async def test_foreign_prefix_not_found(tool):
    import importlib

    from backend import service
    from backend.tools.task_write import TOOL as write
    r = await write.execute({"title": "Bobs Geheimnis"}, make_ctx("bob"))
    bob_id = r.output["task"]["id"]

    mod = importlib.import_module(f"backend.tools.{tool}")
    r2 = await mod.TOOL.execute({"task_id": bob_id[:8]}, make_ctx("alice"))
    assert not r2.success
    assert "Bobs Geheimnis" not in str(r2.output)
    assert service.get_task("bob", bob_id) is not None


@pytest.mark.asyncio
async def test_task_list_filtert_standardmaessig_nach_ctx_projekt():
    """Regression: Projekt-Scope aus Core e51b17ee ging bei der Modul-Übernahme verloren."""
    from backend.tools.task_list import TOOL as lst
    from backend.tools.task_write import TOOL as write

    await write.execute({"title": "In A", "project_id": "a"}, make_ctx())
    await write.execute({"title": "In B", "project_id": "b"}, make_ctx())
    ctx = make_ctx()
    ctx.project_id = "a"

    scoped = await lst.execute({}, ctx)
    assert [t["title"] for t in scoped.output["tasks"]] == ["In A"]
    explicit = await lst.execute({"project_id": "b"}, ctx)
    assert [t["title"] for t in explicit.output["tasks"]] == ["In B"]
