"""Werkzeuge + Verteiler: Zustellung, Trennung der Nutzer, Eingabeprüfung."""
from __future__ import annotations

import json

import pytest

from backend.hub import MAX_CONNECTIONS, QUEUE_SIZE, Hub, TooManyConnections, hub
from backend.tools import NO_HEADSET, TOOLS
from hydrahive.tools.base import ToolContext

TOOL = {t.name: t for t in TOOLS}


def _ctx(user: str) -> ToolContext:
    from pathlib import Path
    return ToolContext(session_id="s", agent_id="a", user_id=user, workspace=Path("/nonexistent"))


async def test_say_reaches_own_headset():
    q = hub.subscribe("alice")
    res = await TOOL["vr_say"].execute({"text": "Hallo Till"}, _ctx("alice"))
    assert res.success
    assert json.loads(q.get_nowait()) == {"type": "say", "text": "Hallo Till"}


async def test_without_headset_fails_honestly():
    res = await TOOL["vr_notify"].execute({"title": "Build", "text": "fertig"}, _ctx("alice"))
    assert not res.success
    assert res.error == NO_HEADSET


async def test_event_never_reaches_other_user():
    q_bob = hub.subscribe("bob")
    res = await TOOL["vr_say"].execute({"text": "geheim"}, _ctx("alice"))
    assert not res.success  # alice hat keine Brille
    assert q_bob.empty()    # bob bekommt nichts


async def test_open_app_validates_app_and_window():
    q = hub.subscribe("alice")
    bad_app = await TOOL["vr_open_app"].execute({"app": "rm -rf"}, _ctx("alice"))
    bad_win = await TOOL["vr_open_app"].execute({"app": "film", "window": 99}, _ctx("alice"))
    assert not bad_app.success and not bad_win.success
    assert q.empty()
    ok = await TOOL["vr_open_app"].execute({"app": "film", "window": 2}, _ctx("alice"))
    assert ok.success
    assert json.loads(q.get_nowait()) == {"type": "open_app", "app": "film", "window": 2}


@pytest.mark.parametrize("args", [{"text": ""}, {"text": "x" * 2001}, {}])
async def test_say_rejects_empty_and_too_long(args):
    q = hub.subscribe("alice")
    res = await TOOL["vr_say"].execute(args, _ctx("alice"))
    assert not res.success
    assert q.empty()


async def test_status_counts_headsets():
    assert (await TOOL["vr_status"].execute({}, _ctx("alice"))).output == {"connected": False, "headsets": 0}
    hub.subscribe("alice")
    assert (await TOOL["vr_status"].execute({}, _ctx("alice"))).output == {"connected": True, "headsets": 1}


def test_connection_limit():
    h = Hub()
    for _ in range(MAX_CONNECTIONS):
        h.subscribe("alice")
    with pytest.raises(TooManyConnections):
        h.subscribe("alice")


def test_full_queue_drops_oldest_instead_of_blocking():
    h = Hub()
    q = h.subscribe("alice")
    for i in range(QUEUE_SIZE + 5):
        h.publish("alice", {"n": i})
    assert q.qsize() == QUEUE_SIZE
    assert json.loads(q.get_nowait())["n"] == 5


def test_unsubscribe_cleans_up():
    h = Hub()
    q = h.subscribe("alice")
    h.unsubscribe("alice", q)
    assert h.connected("alice") == 0
    assert h.publish("alice", {"type": "say", "text": "x"}) == 0
