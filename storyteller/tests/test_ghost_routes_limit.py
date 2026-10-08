"""A1: Kostengrenze bei „Szene schreiben“ (G1) – Schätzung mit Gesamt + Grenze, over_limit/confirm_over_limit."""
from __future__ import annotations

import json
import re


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


def _limit(b, limit):
    return storage.update_book(PROJECT_ID, b["id"], {"ghost": {"limit_tokens": limit}}, base_version=b["version"])


def test_estimate_reports_total_and_limit(client, auth_headers):
    """Spec kostengrenze.md §4: Schätzung gesamt = Eingabe + Ausgabe, dazu die Grenze des Buchs."""
    b, sid = _setup(length=1500)
    _limit(b, 1000)
    e = client.get(f"{P}/books/{b['id']}/ghost/estimate", params={"scene_id": sid}, headers=auth_headers).json()
    assert e["total_tokens"] == e["input_tokens"] + e["output_tokens"] and e["limit_tokens"] == 1000


def test_scene_over_limit_needs_confirmation_and_starts_nothing(client, auth_headers, monkeypatch):
    b, sid = _setup(length=1500)
    _limit(b, 1000)                                   # Ausgabe allein schon ≈ 2.400 > 1000
    calls = _fake(monkeypatch)
    r = client.post(f"{P}/books/{b['id']}/ghost/scene", json={"scene_id": sid}, headers=auth_headers)
    assert r.status_code == 400 and r.json()["detail"]["code"] == "over_limit"
    assert calls == [] and ("testuser", b["id"]) not in ai._busy
    r = client.post(f"{P}/books/{b['id']}/ghost/scene", json={"scene_id": sid, "confirm_over_limit": True},
                    headers=auth_headers)
    assert r.status_code == 200 and len(calls) >= 1


def test_scene_limit_counts_input_too(client, auth_headers, monkeypatch):
    """Ausgabe unter der Grenze, aber Eingabe + Ausgabe darüber → over_limit."""
    from backend import _cost
    monkeypatch.setattr(_cost, "scene_estimate", lambda *a, **k: {"sections": 1, "input_tokens": 900, "output_tokens": 500})
    b, sid = _setup()
    _limit(b, 1000)
    _fake(monkeypatch)
    r = client.post(f"{P}/books/{b['id']}/ghost/scene", json={"scene_id": sid}, headers=auth_headers)
    assert r.status_code == 400 and r.json()["detail"]["code"] == "over_limit"


def test_scene_without_limit_needs_no_confirmation(client, auth_headers, monkeypatch):
    b, sid = _setup(length=1500)
    _fake(monkeypatch)
    r = client.post(f"{P}/books/{b['id']}/ghost/scene", json={"scene_id": sid}, headers=auth_headers)
    assert r.status_code == 200
