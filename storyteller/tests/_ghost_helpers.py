"""Gemeinsame Bausteine der Ghostwriter-G2-Tests: Testbuch mit Szenen + gefälschtes Modell."""
from __future__ import annotations

import re

from conftest import PROJECT_ID

from backend import ghost, storage


def make_book(n_scenes=3, texts=None, summaries=None, length=300, limit=0, model="claude-sonnet-4-6"):
    """Buch mit n Szenen in Kapitel 1, alle mit Zusammenfassung (außer in ``summaries`` leer gesetzt).
    Gibt (book_id, chapter_id, scene_ids) zurück."""
    b = storage.create_book(PROJECT_ID, {"title": "T", "kind": "novel", "language": "de"})
    ch = storage.get_structure(PROJECT_ID, b["id"])["parts"][0]["chapters"][0]
    sids = [ch["scenes"][0]]
    for i in range(1, n_scenes):
        sids.append(storage.add_scene(PROJECT_ID, b["id"], ch["id"], f"S{i}", after=sids[-1])["scene"]["id"])
    for i, sid in enumerate(sids):
        data = {"summary": (summaries or {}).get(i, f"Szene {i} passiert.")}
        if texts and i in texts:
            data["text"] = texts[i]
        storage.save_scene(PROJECT_ID, b["id"], sid, data, base_version=storage.get_scene(PROJECT_ID, b["id"], sid)["version"])
    b = storage.update_book(PROJECT_ID, b["id"], {"ghost": {"model": model, "length_words": length, "limit_tokens": limit}},
                            base_version=b["version"])
    return b["id"], ch["id"], sids


def fake_llm(monkeypatch, *, words=300, calls=None, fail_on=None, hook=None, summary="Kurz zusammengefasst."):
    """Modell fälschen: jeder Aufruf liefert „Text<n> wort wort …“ (words Wörter). ``hook(n)`` läuft vor dem
    Liefern (z. B. Autor tippt, Abbruch), ``fail_on`` = Nummer des Aufrufs, der scheitert."""
    calls = calls if calls is not None else []

    async def fake_stream(messages, model=None, temperature=0.7, max_tokens=4096):
        calls.append({"model": model, "messages": messages})
        n = len(calls)
        if hook:
            await hook(n)
        if fail_on and n == fail_on:
            raise RuntimeError("Modell weg")
        for part in re.findall(r"\S+\s*", f"Text{n} " + "wort " * (words - 1)):
            yield part

    async def fake_complete(messages, model=None, temperature=0.7, max_tokens=4096):
        return summary
    monkeypatch.setattr(ghost, "stream", fake_stream)
    monkeypatch.setattr(ghost, "complete", fake_complete)
    return calls
