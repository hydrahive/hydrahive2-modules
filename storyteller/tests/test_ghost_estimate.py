"""Ghostwriter G1: Schätzung gegen echte Anfragen und Abbruch durch den Browser."""
from __future__ import annotations

import json
import re

import pytest

from conftest import MOD_PREFIX, PROJECT_ID

from backend import ai, ghost, storage

P = f"{MOD_PREFIX}/projects/{PROJECT_ID}"


def _setup(length=600, chunk=300, model="test/m"):
    b = storage.create_book(PROJECT_ID, {"title": "T", "kind": "novel", "language": "de"})
    sid = storage.get_structure(PROJECT_ID, b["id"])["parts"][0]["chapters"][0]["scenes"][0]
    storage.save_scene(PROJECT_ID, b["id"], sid, {"summary": "Gregor erwacht."}, base_version=1)
    b = storage.update_book(PROJECT_ID, b["id"], {"ghost": {"model": model, "length_words": length, "chunk_words": chunk}},
                            base_version=b["version"])
    return b, sid


def _fake(monkeypatch, text_per_call="wort " * 300, calls=None, fail=False):
    calls = calls if calls is not None else []

    async def fake_stream(messages, model=None, temperature=0.7, max_tokens=4096):
        calls.append({"model": model, "messages": messages})
        if fail:
            raise RuntimeError("Schlüssel fehlt")
        for part in re.findall(r"\S+\s*", text_per_call):
            yield part
    monkeypatch.setattr(ghost, "stream", fake_stream)
    return calls


def _events(body: str) -> list[dict]:
    out = []
    for block in body.strip().split("\n\n"):
        ev = {k: v for k, v in (line.split(": ", 1) for line in block.splitlines() if ": " in line)}
        if "data" in ev:
            ev["data"] = json.loads(ev["data"])
        out.append(ev)
    return out


def _files(book_id):
    d = storage.book_dir(PROJECT_ID, book_id)
    return {p.relative_to(d).as_posix(): p.read_bytes() for p in d.rglob("*") if p.is_file()}


@pytest.mark.parametrize("length,chunk", [(900, 300), (2500, 700)])
def test_estimate_matches_what_a_run_actually_sends(client, auth_headers, monkeypatch, length, chunk):
    """Schätzung der Eingabe gegen die tatsächlich gesendeten Anfragen (Zeichen/4), ±35 % – auch mit 4 Abschnitten."""
    b, sid = _setup(length=length, chunk=chunk)
    calls = _fake(monkeypatch)
    est = client.get(f"{P}/books/{b['id']}/ghost/estimate", params={"scene_id": sid}, headers=auth_headers).json()
    client.post(f"{P}/books/{b['id']}/ghost/scene", json={"scene_id": sid}, headers=auth_headers)
    sent = sum(len(m["content"]) for c in calls for m in c["messages"]) // 4
    assert est["sections"] == len(calls)
    assert 0.65 * sent <= est["input_tokens"] <= 1.35 * sent, (est["input_tokens"], sent)


def test_client_abort_releases_lock_and_stops_model(monkeypatch):
    """Browser schließt den Stream mitten im Lauf → Generator wird geschlossen, Sperre frei, kein weiterer Abschnitt."""
    import asyncio

    from backend import ghost_routes
    b, sid = _setup(length=1200, chunk=300)
    calls = _fake(monkeypatch)

    class Body:
        scene_id = sid
        length_words = None
        model = None

    model_stream_closed: list[bool] = []

    async def slow_stream(messages, model=None, temperature=0.7, max_tokens=4096):
        calls.append({"model": model})
        try:
            for _ in range(10_000):
                await asyncio.sleep(0)
                yield "wort "
        finally:
            model_stream_closed.append(True)   # Verbindung zum Modell wird geschlossen
    monkeypatch.setattr(ghost, "stream", slow_stream)

    async def run():
        resp = await ghost_routes.ghost_scene(PROJECT_ID, b["id"], Body(), ("testuser", "user"))
        it = resp.body_iterator
        first = await it.__anext__()
        assert ("testuser", b["id"]) in ai._busy
        await it.aclose()                     # so beendet Starlette den Generator beim Verbindungsabbruch
        return first, list(model_stream_closed)
    first, closed_at_abort = asyncio.run(run())
    assert first.startswith("event: delta")
    assert ("testuser", b["id"]) not in ai._busy and len(calls) == 1
    assert closed_at_abort == [True]          # sofort, nicht erst irgendwann beim Aufräumen
