"""Ghostwriter G1: Endpunkte (Server-Sent Events), Sperren, Rechte, Schätzung, Gedächtnis."""
from __future__ import annotations

import json
import re

from conftest import MOD_PREFIX, OTHER_PROJECT_ID, PROJECT_ID

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


def test_scene_stream_delivers_text_and_changes_no_file(client, auth_headers, monkeypatch):
    b, sid = _setup()
    calls = _fake(monkeypatch)
    before = _files(b["id"])
    r = client.post(f"{P}/books/{b['id']}/ghost/scene", json={"scene_id": sid}, headers=auth_headers)
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/event-stream")
    evs = _events(r.text)
    assert {e["event"] for e in evs} == {"delta", "done"}
    text = "".join(e["data"]["text"] for e in evs if e["event"] == "delta")
    done = evs[-1]
    assert done["event"] == "done" and done["data"]["words"] == len(text.split()) and done["data"]["model"] == "test/m"
    assert done["data"]["mode"] == "fill" and len(text.split()) >= 600 * 0.85
    assert calls[0]["model"] == "test/m"
    assert _files(b["id"]) == before                               # Vorschlag – nichts geschrieben


def test_request_overrides_length_and_model(client, auth_headers, monkeypatch):
    b, sid = _setup()
    calls = _fake(monkeypatch)
    r = client.post(f"{P}/books/{b['id']}/ghost/scene", json={"scene_id": sid, "length_words": 300, "model": "anders/m"}, headers=auth_headers)
    assert r.status_code == 200 and len(calls) == 1 and calls[0]["model"] == "anders/m"


def test_missing_length_and_summary_are_clear_errors(client, auth_headers, monkeypatch):
    _fake(monkeypatch)
    b, sid = _setup(length=0, chunk=0)
    r = client.post(f"{P}/books/{b['id']}/ghost/scene", json={"scene_id": sid}, headers=auth_headers)
    assert r.status_code == 400 and r.json()["detail"]["code"] == "length_required"
    storage.save_scene(PROJECT_ID, b["id"], sid, {"summary": ""}, base_version=storage.get_scene(PROJECT_ID, b["id"], sid)["version"])
    r = client.post(f"{P}/books/{b['id']}/ghost/scene", json={"scene_id": sid, "length_words": 500}, headers=auth_headers)
    assert r.status_code == 400 and r.json()["detail"]["code"] == "summary_required"


def test_rights_reader_403_foreign_404(client, auth_headers, reader_headers, monkeypatch):
    _fake(monkeypatch)
    b, sid = _setup()
    assert client.post(f"{P}/books/{b['id']}/ghost/scene", json={"scene_id": sid}, headers=reader_headers).status_code == 403
    assert client.post(f"{MOD_PREFIX}/projects/{OTHER_PROJECT_ID}/books/{b['id']}/ghost/scene", json={"scene_id": sid},
                       headers=auth_headers).status_code == 404
    assert client.get(f"{P}/books/{b['id']}/ghost/estimate", params={"scene_id": sid}, headers=reader_headers).status_code == 200


def test_busy_lock_shared_with_suggest_and_released(client, auth_headers, monkeypatch):
    _fake(monkeypatch)
    b, sid = _setup()
    ai._busy.add(("testuser", b["id"]))
    r = client.post(f"{P}/books/{b['id']}/ghost/scene", json={"scene_id": sid}, headers=auth_headers)
    assert r.status_code == 409 and r.json()["detail"]["code"] == "ai_busy"
    ai._busy.discard(("testuser", b["id"]))
    assert client.post(f"{P}/books/{b['id']}/ghost/scene", json={"scene_id": sid}, headers=auth_headers).status_code == 200
    assert ("testuser", b["id"]) not in ai._busy                     # nach dem Lauf wieder frei


def test_rate_limit_counts_with_suggest(client, auth_headers, monkeypatch):
    _fake(monkeypatch)
    b, sid = _setup()
    monkeypatch.setattr(ai, "RATE_PER_MINUTE", 1)
    assert client.post(f"{P}/books/{b['id']}/ghost/scene", json={"scene_id": sid}, headers=auth_headers).status_code == 200
    r = client.post(f"{P}/books/{b['id']}/ghost/scene", json={"scene_id": sid}, headers=auth_headers)
    assert r.status_code == 429


def test_llm_error_becomes_error_event_and_frees_lock(client, auth_headers, monkeypatch):
    _fake(monkeypatch, fail=True)
    b, sid = _setup()
    r = client.post(f"{P}/books/{b['id']}/ghost/scene", json={"scene_id": sid}, headers=auth_headers)
    evs = _events(r.text)
    assert evs[-1]["event"] == "error" and "Schlüssel fehlt" in evs[-1]["data"]["message"]
    assert ("testuser", b["id"]) not in ai._busy


def test_estimate_uses_settings_no_fixed_values(client, auth_headers):
    b, sid = _setup(length=1500, model="schaetz/m")
    r = client.get(f"{P}/books/{b['id']}/ghost/estimate", params={"scene_id": sid}, headers=auth_headers)
    assert r.status_code == 200
    e = r.json()
    assert e["model"] == "schaetz/m" and e["length_words"] == 1500
    assert e["output_tokens"] >= 1500 and e["input_tokens"] > 0 and e["sections"] >= 1


def test_summarize_writes_only_empty_summary(client, auth_headers, monkeypatch):
    b, sid = _setup()

    async def fake_complete(messages, model=None, temperature=0.7, max_tokens=4096):
        return "# Zusammenfassung\n\nGregor erwacht und sorgt sich um die Arbeit."
    monkeypatch.setattr(ghost, "complete", fake_complete)
    v = storage.get_scene(PROJECT_ID, b["id"], sid)["version"]
    storage.save_scene(PROJECT_ID, b["id"], sid, {"text": "Langer Text.", "summary": ""}, base_version=v)
    r = client.post(f"{P}/books/{b['id']}/ghost/summarize", json={"scene_id": sid}, headers=auth_headers)
    assert r.status_code == 200 and r.json()["kept"] is False
    s = storage.get_scene(PROJECT_ID, b["id"], sid)
    assert s["summary"] == "Gregor erwacht und sorgt sich um die Arbeit."      # bereinigt
    r = client.post(f"{P}/books/{b['id']}/ghost/summarize", json={"scene_id": sid}, headers=auth_headers)
    assert r.json()["kept"] is True and storage.get_scene(PROJECT_ID, b["id"], sid)["version"] == s["version"]


def test_estimate_matches_what_a_run_actually_sends(client, auth_headers, monkeypatch):
    """Schätzung der Eingabe gegen die tatsächlich gesendeten Anfragen (Zeichen/4), ±35 %."""
    b, sid = _setup(length=900, chunk=300)
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
