"""Verlauf statt Überschreiben (Task df2f2eb2, SPEC-HISTORY.md)."""
from __future__ import annotations

import re
from pathlib import Path

import pytest
from hydrahive.tools.base import ToolContext

from backend import service
from backend.tools import task_read, task_write


def _task(user: str = "alice", **kw) -> dict:
    return service.create_task(user, title=kw.pop("title", "Titel"), description=kw.pop("description", "Analyse A"), **kw)


# ── Sichern beim Ändern ───────────────────────────────────────────────────

def test_description_change_keeps_old_version():
    t = _task()
    service.update_task("alice", t["id"], description="Neu B")
    hist = service.history("alice", t["id"])
    assert [h["description"] for h in hist] == ["Analyse A"]
    assert hist[0]["title"] == "Titel" and hist[0]["source"] == "update"
    assert service.get_task("alice", t["id"])["description"] == "Neu B"


def test_title_change_keeps_old_version():
    t = _task()
    service.update_task("alice", t["id"], title="Anderer Titel")
    assert [h["title"] for h in service.history("alice", t["id"])] == ["Titel"]


def test_every_change_is_kept_newest_first():
    t = _task()
    for text in ("B", "C", "D"):
        service.update_task("alice", t["id"], description=text)
    assert [h["description"] for h in service.history("alice", t["id"])] == ["C", "B", "Analyse A"]


def test_same_value_creates_no_entry():
    t = _task()
    service.update_task("alice", t["id"], description="Analyse A", title="Titel")
    assert service.history("alice", t["id"]) == []


def test_status_or_priority_only_creates_no_entry():
    t = _task()
    service.update_task("alice", t["id"], status="done", priority="high")
    assert service.history("alice", t["id"]) == []


def test_failed_update_creates_no_entry():
    t = _task()
    with pytest.raises(ValueError):
        service.update_task("alice", t["id"], description="X", status="kaputt")
    assert service.history("alice", t["id"]) == []
    assert service.get_task("alice", t["id"])["description"] == "Analyse A"


def test_foreign_task_history_invisible():
    t = _task()
    service.update_task("alice", t["id"], description="B")
    assert service.history("bob", t["id"]) is None


def test_delete_task_removes_history():
    t = _task()
    service.update_task("alice", t["id"], description="B")
    assert service.delete_task("alice", t["id"])
    from hydrahive.db.connection import db
    with db() as c:
        n = c.execute("SELECT COUNT(*) FROM module_tasks_history WHERE task_id = ?", (t["id"],)).fetchone()[0]
    assert n == 0


# ── note: anhängen ────────────────────────────────────────────────────────

def test_note_appends_with_timestamp():
    t = _task()
    service.update_task("alice", t["id"], note="PR #1 offen")
    desc = service.get_task("alice", t["id"])["description"]
    assert desc.startswith("Analyse A\n\n[")
    assert re.search(r"\n\n\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}\] PR #1 offen$", desc)
    assert [h["description"] for h in service.history("alice", t["id"])] == ["Analyse A"]


def test_note_on_empty_description_has_no_leading_blank_lines():
    t = _task(description="")
    service.update_task("alice", t["id"], note="erste Notiz")
    assert re.fullmatch(r"\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}\] erste Notiz", service.get_task("alice", t["id"])["description"])


def test_empty_note_is_ignored():
    t = _task()
    service.update_task("alice", t["id"], note="   ")
    assert service.get_task("alice", t["id"])["description"] == "Analyse A"
    assert service.history("alice", t["id"]) == []


def test_description_and_note_replace_then_append():
    t = _task()
    service.update_task("alice", t["id"], description="Korrigiert", note="Grund")
    desc = service.get_task("alice", t["id"])["description"]
    assert desc.startswith("Korrigiert\n\n[") and desc.endswith("] Grund")
    assert len(service.history("alice", t["id"])) == 1


# ── Limit ─────────────────────────────────────────────────────────────────

def test_history_limit_drops_oldest_update_keeps_restored(monkeypatch):
    monkeypatch.setattr(service, "HISTORY_LIMIT", 3)
    t = _task()
    service.add_restored("alice", t["id"], title="Titel", description="aus Chat", seen_at="2026-08-01T10:00:00Z")
    for text in ("B", "C", "D", "E"):
        service.update_task("alice", t["id"], description=text)
    hist = service.history("alice", t["id"])
    assert len(hist) == 3
    assert any(h["source"] == "restored" and h["description"] == "aus Chat" for h in hist)
    assert [h["description"] for h in hist if h["source"] == "update"] == ["D", "C"]


# ── Wiederherstellung ─────────────────────────────────────────────────────

def test_add_restored_is_idempotent_and_owner_bound():
    t = _task()
    assert service.add_restored("alice", t["id"], title="T", description="alt", seen_at="2026-08-01T10:00:00Z") is True
    assert service.add_restored("alice", t["id"], title="T", description="alt", seen_at="2026-08-01T10:00:00Z") is False
    assert service.add_restored("bob", t["id"], title="T", description="fremd", seen_at="2026-08-01T10:00:00Z") is False
    hist = service.history("alice", t["id"])
    assert len(hist) == 1 and hist[0]["source"] == "restored" and hist[0]["changed_at"] == "2026-08-01T10:00:00Z"


def test_history_count():
    t = _task()
    service.update_task("alice", t["id"], description="B")
    service.update_task("alice", t["id"], description="C")
    assert service.history_counts("alice") == {t["id"]: 2}


def test_history_count_only_own_tasks():
    mine = _task()
    theirs = _task(user="bob")
    service.update_task("alice", mine["id"], description="B")
    service.update_task("bob", theirs["id"], description="X")
    assert service.history_counts("alice") == {mine["id"]: 1}
    assert service.history_counts("bob") == {theirs["id"]: 1}


# ── Tools ─────────────────────────────────────────────────────────────────





def _ctx(user: str = "alice") -> ToolContext:
    return ToolContext(session_id="s1", agent_id="a1", user_id=user, workspace=Path("/tmp"))


@pytest.mark.asyncio
async def test_task_write_note_appends_and_keeps_history():
    t = _task()
    r = await task_write.TOOL.execute({"title": "Titel", "task_id": t["id"], "note": "Befund X"}, _ctx())
    assert r.success
    assert r.output["task"]["description"].startswith("Analyse A\n\n[")
    assert r.output["task"]["description"].endswith("] Befund X")


@pytest.mark.asyncio
async def test_task_write_description_replace_keeps_history():
    t = _task()
    await task_write.TOOL.execute({"title": "Titel", "task_id": t["id"], "description": "Neu"}, _ctx())
    assert [h["description"] for h in service.history("alice", t["id"])] == ["Analyse A"]


def test_task_write_schema_explains_replace_and_note():
    props = task_write.TOOL.schema["properties"]
    assert "note" in props
    assert "ERSETZT" in props["description"]["description"]
    assert "note" in task_write.TOOL.prompt_hint


@pytest.mark.asyncio
async def test_task_read_shows_history_count_and_history():
    t = _task()
    service.update_task("alice", t["id"], description="B")
    short = await task_read.TOOL.execute({"task_id": t["id"]}, _ctx())
    assert "1 frühere Fassung" in short.output["summary"]
    assert "history" not in short.output
    full = await task_read.TOOL.execute({"task_id": t["id"], "history": True}, _ctx())
    assert full.output["history"][0]["description"] == "Analyse A"
    assert "Analyse A" in full.output["summary"]


@pytest.mark.asyncio
async def test_task_read_without_history_has_no_counter():
    t = _task()
    r = await task_read.TOOL.execute({"task_id": t["id"]}, _ctx())
    assert "frühere Fassung" not in r.output["summary"]


# ── API ───────────────────────────────────────────────────────────────────

BASE = "/api/modules/tasks/tasks"


def test_api_patch_description_keeps_history_and_get_history(client, alice, bob):
    tid = client.post(BASE, json={"title": "T", "description": "alt"}, headers=alice).json()["id"]
    assert client.patch(f"{BASE}/{tid}", json={"description": "neu"}, headers=alice).status_code == 200
    r = client.get(f"{BASE}/{tid}/history", headers=alice)
    assert r.status_code == 200 and [h["description"] for h in r.json()] == ["alt"]
    assert client.get(f"{BASE}/{tid}/history", headers=bob).status_code == 404


def test_api_patch_note_appends(client, alice):
    tid = client.post(BASE, json={"title": "T", "description": "alt"}, headers=alice).json()["id"]
    r = client.patch(f"{BASE}/{tid}", json={"note": "Notiz"}, headers=alice)
    assert r.json()["description"].startswith("alt\n\n[") and r.json()["description"].endswith("] Notiz")


def test_api_list_has_history_count(client, alice):
    tid = client.post(BASE, json={"title": "T", "description": "alt"}, headers=alice).json()["id"]
    other = client.post(BASE, json={"title": "U"}, headers=alice).json()["id"]
    client.patch(f"{BASE}/{tid}", json={"description": "neu"}, headers=alice)
    rows = {t["id"]: t for t in client.get(BASE, headers=alice).json()}
    assert rows[tid]["history_count"] == 1 and rows[other]["history_count"] == 0
