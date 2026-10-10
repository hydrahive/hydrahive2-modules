"""SSE-Kanal: Login-Pflicht, Status, Zustellung über die echte Route."""
from __future__ import annotations

import asyncio
import json

from backend.hub import hub
from conftest import MOD_PREFIX


def test_events_requires_login(client):
    assert client.get(f"{MOD_PREFIX}/events").status_code == 401
    assert client.get(f"{MOD_PREFIX}/status").status_code == 401


def test_status_without_headset(client, login):
    r = client.get(f"{MOD_PREFIX}/status", headers=login("alice"))
    assert r.status_code == 200
    assert r.json() == {"headsets": 0}


async def test_stream_delivers_only_own_events(setup_test_env):
    """Ruft die Route direkt auf (TestClient kann endlose SSE nicht sauber lesen)."""
    from backend.routes import events_stream

    resp = await events_stream(("alice", "user"))
    gen = resp.body_iterator
    assert await anext(gen) == ": connected\n\n"
    assert hub.connected("alice") == 1

    hub.publish("bob", {"type": "say", "text": "für bob"})
    hub.publish("alice", {"type": "say", "text": "für alice"})
    chunk = await asyncio.wait_for(anext(gen), timeout=2)
    assert chunk.startswith("data: ")
    assert json.loads(chunk[len("data: "):]) == {"type": "say", "text": "für alice"}

    await gen.aclose()
    assert hub.connected("alice") == 0
