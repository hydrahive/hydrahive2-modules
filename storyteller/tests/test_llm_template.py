"""Storyteller fragt ohne eigenes Modell die Rolle `storyteller-ghostwriter` an (Kern E5)."""
from __future__ import annotations

import asyncio

from backend import _llm


def test_ohne_modell_kommt_template(monkeypatch):
    seen = {}

    async def fake(messages, model=None, temperature=0.7, max_tokens=4096, **kw):
        seen.update(model=model, **kw)
        return "ok"
    monkeypatch.setattr(_llm._client, "complete", fake)
    monkeypatch.setattr(_llm._client, "SUPPORTS_TEMPLATE", True, raising=False)
    assert asyncio.run(_llm.complete([{"role": "user", "content": "x"}])) == "ok"
    assert seen == {"model": None, "template": "storyteller-ghostwriter"}


def test_eigenes_modell_bleibt(monkeypatch):
    seen = {}

    async def fake(messages, model=None, temperature=0.7, max_tokens=4096, **kw):
        seen.update(model=model, **kw)
        return "ok"
    monkeypatch.setattr(_llm._client, "complete", fake)
    monkeypatch.setattr(_llm._client, "SUPPORTS_TEMPLATE", True, raising=False)
    asyncio.run(_llm.complete([{"role": "user", "content": "x"}], model="claude-sonnet-4-6"))
    assert seen == {"model": "claude-sonnet-4-6"}


def test_alter_kern_ohne_template(monkeypatch):
    seen = {}

    async def fake(messages, model=None, temperature=0.7, max_tokens=4096, **kw):
        seen.update(model=model, **kw)
        return "ok"
    monkeypatch.setattr(_llm._client, "complete", fake)
    monkeypatch.delattr(_llm._client, "SUPPORTS_TEMPLATE", raising=False)
    asyncio.run(_llm.complete([{"role": "user", "content": "x"}]))
    assert seen == {"model": None}


def test_stream_ohne_modell_kommt_template(monkeypatch):
    seen = {}

    async def fake(messages, model=None, temperature=0.7, max_tokens=4096, **kw):
        seen.update(model=model, **kw)
        yield "a"
    monkeypatch.setattr(_llm._client, "stream", fake)
    monkeypatch.setattr(_llm._client, "SUPPORTS_TEMPLATE", True, raising=False)

    async def run():
        return [c async for c in _llm.stream([{"role": "user", "content": "x"}])]
    assert asyncio.run(run()) == ["a"]
    assert seen["template"] == "storyteller-ghostwriter"


def test_manifest_template():
    import json
    from pathlib import Path
    m = json.loads((Path(__file__).resolve().parents[1] / "manifest.json").read_text())
    assert m["templates"] == [{"id": "storyteller-ghostwriter", "label": "Storyteller (Schreib-Team)",
                               "base": "modul-schreiber"}]
