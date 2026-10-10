"""vr 0.2: Fenster schließen, Layout, Mediensteuerung, Fensterstand (Rückkanal)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.hub import hub
from backend.tools import TOOLS
from conftest import MOD_PREFIX
from hydrahive.tools.base import ToolContext

TOOL = {t.name: t for t in TOOLS}


def _ctx(user: str) -> ToolContext:
    return ToolContext(session_id="s", agent_id="a", user_id=user, workspace=Path("/nonexistent"))


async def _fire(name: str, args: dict, user: str = "alice"):
    return await TOOL[name].execute(args, _ctx(user))


async def test_close_window():
    q = hub.subscribe("alice")
    assert (await _fire("vr_close_window", {"window": 3})).success
    assert json.loads(q.get_nowait()) == {"type": "close_window", "window": 3}


@pytest.mark.parametrize("w", [0, 9, "x", None])
async def test_close_window_rejects_bad_numbers(w):
    q = hub.subscribe("alice")
    assert not (await _fire("vr_close_window", {"window": w})).success
    assert q.empty()


async def test_layout_keeps_order():
    q = hub.subscribe("alice")
    assert (await _fire("vr_layout", {"apps": ["chat", "monitor", "book"]})).success
    assert json.loads(q.get_nowait()) == {"type": "layout", "apps": ["chat", "monitor", "book"]}


@pytest.mark.parametrize("apps", [[], ["chat"] * 9, ["chat", "evil"], "chat"])
async def test_layout_rejects_invalid(apps):
    q = hub.subscribe("alice")
    assert not (await _fire("vr_layout", {"apps": apps})).success
    assert q.empty()


async def test_media_with_and_without_app():
    q = hub.subscribe("alice")
    assert (await _fire("vr_media", {"action": "pause"})).success
    assert (await _fire("vr_media", {"action": "next", "app": "music"})).success
    assert json.loads(q.get_nowait()) == {"type": "media", "action": "pause"}
    assert json.loads(q.get_nowait()) == {"type": "media", "action": "next", "app": "music"}
    assert not (await _fire("vr_media", {"action": "rewind"})).success
    assert not (await _fire("vr_media", {"action": "play", "app": "chat"})).success
    assert q.empty()


async def test_windows_unknown_until_reported():
    r = await _fire("vr_windows", {})
    assert r.success and r.output["known"] is False


def test_state_report_and_isolation(client, login):
    a, b = login("alice"), login("bob")
    body = {"windows": [{"window": 2, "app": "film"}, {"window": 1, "app": "chat"}, {"window": 3, "app": None}]}
    r = client.put(f"{MOD_PREFIX}/state", json=body, headers=a)
    assert r.status_code == 200
    assert [w["window"] for w in r.json()["windows"]] == [1, 2, 3]  # sortiert

    from backend import state
    assert state.get("alice")["windows"][1] == {"window": 2, "app": "film"}
    assert state.get("bob") is None  # bob sieht alices Stand nicht
    assert client.put(f"{MOD_PREFIX}/state", json={"windows": []}, headers=b).status_code == 200
    assert state.get("alice")["windows"] != []  # bob überschreibt alice nicht


@pytest.mark.parametrize("windows", [
    [{"window": 9, "app": "chat"}],
    [{"window": 1, "app": "evil"}],
    [{"window": 1, "app": "chat"}, {"window": 1, "app": "film"}],
    [{"window": i, "app": "chat"} for i in range(1, 10)],
])
def test_state_rejects_invalid(client, login, windows):
    r = client.put(f"{MOD_PREFIX}/state", json={"windows": windows}, headers=login("alice"))
    assert r.status_code == 422


def test_state_requires_login(client):
    assert client.put(f"{MOD_PREFIX}/state", json={"windows": []}).status_code == 401


async def test_windows_after_report():
    from backend import state
    state.report("alice", [{"window": 1, "app": "chat"}])
    r = await _fire("vr_windows", {})
    assert r.output["known"] is True
    assert r.output["windows"] == [{"window": 1, "app": "chat"}]
