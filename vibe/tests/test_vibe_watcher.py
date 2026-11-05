"""Baustein 6: Zug-Ende erkennen und genau eine Version speichern (PLAN-V1.md Entscheidung 3, geändert 5.11.).

Der Hörer ist ein Poller (`ctx.register_job`): Pro aktivem Vibe-Projekt wird `is_running(session)` abgefragt; der Wechsel
„läuft → läuft nicht“ ist das Zug-Ende. Grund (am Kern gemessen): `bus.open()` startet je Lauf einen frischen Kanal, ein
vorher angehängter Hörer bekäme nichts.
"""
from __future__ import annotations

import asyncio

import pytest
from backend import watcher

MODEL = "claude-sonnet-4-6"


def run(coro):
    return asyncio.run(coro)


class Kern:
    """Stand-in für den Kern: welche Sitzungen laufen, was die letzte Antwort sagte."""

    def __init__(self) -> None:
        self.running: set[str] = set()
        self.last_text: dict[str, str] = {}
        self.commits: list[tuple[str, str, str]] = []


@pytest.fixture
def kern(monkeypatch):
    k = Kern()
    monkeypatch.setattr(watcher, "_is_running", lambda sid: sid in k.running)
    monkeypatch.setattr(watcher, "_last_reply", lambda sid: k.last_text.get(sid, ""))

    async def fake_commit(pid, text, *, kind="turn"):
        k.commits.append((pid, text, kind))
        return {"commit_id": "c" * 40, "summary": text, "kind": kind, "created_at": "x"}
    monkeypatch.setattr(watcher.versions, "commit_turn", fake_commit)
    monkeypatch.setattr(watcher, "_sessions", lambda: {"p1": "s1"})
    watcher.reset()
    return k


def tick():
    return run(watcher.poll())


def test_zug_laeuft_noch_keine_version(kern):
    kern.running.add("s1")
    tick()
    assert kern.commits == []


def test_zug_ende_genau_eine_version(kern):
    kern.running.add("s1")
    kern.last_text["s1"] = "Hintergrund dunkelblau\n\nDetails"
    tick()
    kern.running.discard("s1")
    tick()
    assert [(p, t, k) for p, t, k in kern.commits] == [("p1", "Hintergrund dunkelblau\n\nDetails", "turn")]


def test_kein_zug_keine_version_auch_bei_vielen_ticks(kern):
    for _ in range(5):
        tick()
    assert kern.commits == []


def test_nach_dem_ende_nicht_nochmal(kern):
    kern.running.add("s1")
    tick()
    kern.running.discard("s1")
    tick()
    tick()
    tick()
    assert len(kern.commits) == 1


def test_zwei_zuege_hintereinander_zwei_versionen(kern):
    for text in ("eins", "zwei"):
        kern.running.add("s1")
        kern.last_text["s1"] = text
        tick()
        kern.running.discard("s1")
        tick()
    assert [t for _, t, _ in kern.commits] == ["eins", "zwei"]


def test_kurzer_zug_zwischen_zwei_ticks_wird_nicht_verpasst(kern):
    """Ein Zug, der zwischen zwei Abfragen beginnt und endet, ist für den Poller unsichtbar. Darum merkt sich der
    Hörer zusätzlich die Nachrichtenzahl der Sitzung: ändert sie sich, gab es einen Zug."""
    kern.last_text["s1"] = "erste Antwort"
    watcher.reset()
    tick()                                   # Stand merken
    kern.last_text["s1"] = "zweite Antwort"  # inzwischen ein ganzer Zug, nie als „läuft“ gesehen
    tick()
    assert [t for _, t, _ in kern.commits] == ["zweite Antwort"]


def test_zwei_projekte_getrennt(kern, monkeypatch):
    monkeypatch.setattr(watcher, "_sessions", lambda: {"p1": "s1", "p2": "s2"})
    kern.running.update({"s1", "s2"})
    kern.last_text.update({"s1": "a", "s2": "b"})
    tick()
    kern.running.discard("s2")
    tick()
    assert kern.commits == [("p2", "b", "turn")]


def test_projekt_ohne_sitzung_wird_uebersprungen(kern, monkeypatch):
    monkeypatch.setattr(watcher, "_sessions", lambda: {"p1": None})
    tick()
    assert kern.commits == []


def test_fehler_bei_einem_projekt_stoppt_die_anderen_nicht(kern, monkeypatch):
    monkeypatch.setattr(watcher, "_sessions", lambda: {"p1": "s1", "p2": "s2"})
    kern.running.update({"s1", "s2"})
    kern.last_text.update({"s1": "a", "s2": "b"})
    tick()
    kern.running.clear()
    orig = watcher.versions.commit_turn

    async def mal_kaputt(pid, text, *, kind="turn"):
        if pid == "p1":
            raise RuntimeError("Container aus")
        return await orig(pid, text, kind=kind)
    monkeypatch.setattr(watcher.versions, "commit_turn", mal_kaputt)
    tick()
    assert ("p2", "b", "turn") in kern.commits


def test_fehlgeschlagener_commit_wird_beim_naechsten_tick_wiederholt(kern, monkeypatch):
    kern.running.add("s1")
    kern.last_text["s1"] = "wichtig"
    tick()
    kern.running.discard("s1")
    calls = {"n": 0}
    orig = watcher.versions.commit_turn

    async def erst_kaputt(pid, text, *, kind="turn"):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("kurz weg")
        return await orig(pid, text, kind=kind)
    monkeypatch.setattr(watcher.versions, "commit_turn", erst_kaputt)
    tick()
    tick()
    assert calls["n"] == 2 and [t for _, t, _ in kern.commits] == ["wichtig"]


def test_neustart_vergisst_laufende_zuege_ohne_phantomversion(kern):
    kern.running.add("s1")
    tick()
    watcher.reset()                           # Server-Neustart: Zustand weg, der Zug ist nicht mehr da
    kern.running.discard("s1")
    tick()
    assert kern.commits == []


def test_pause_wenn_projekt_gelöscht_wird(kern, monkeypatch):
    kern.running.add("s1")
    tick()
    monkeypatch.setattr(watcher, "_sessions", lambda: {})
    kern.running.discard("s1")
    tick()
    assert kern.commits == []
    assert "p1" not in watcher._state


# --- Start: Der Kern ruft register() VOR den Migrationen auf (an hydratest 5.11. gemessen: „no such table“) -------

class _Ctx:
    def __init__(self) -> None:
        self.jobs: list[tuple] = []

    def register_migrations(self, rel):
        pass

    def register_router(self, router):
        pass

    def register_job(self, name, fn, interval, **kw):
        self.jobs.append((name, fn, interval))


def test_register_beruehrt_die_datenbank_nicht(monkeypatch):
    import backend
    from backend import state

    def boom(*a, **k):
        raise RuntimeError("Tabelle gibt es beim register() noch nicht")
    monkeypatch.setattr(state, "all_rows", boom)
    ctx = _Ctx()
    backend.register(ctx)                                   # darf nicht werfen
    assert [j[0] for j in ctx.jobs] == ["vibe-watcher"]


def test_erster_durchlauf_holt_unterbrochene_auftraege_nach_genau_einmal(kern, monkeypatch):
    from backend import jobs
    calls = {"n": 0}
    monkeypatch.setattr(jobs, "recover_after_restart", lambda: calls.__setitem__("n", calls["n"] + 1))
    tick()
    tick()
    tick()
    assert calls["n"] == 1


def test_fehler_beim_nachholen_stoppt_den_waechter_nicht(kern, monkeypatch):
    from backend import jobs

    def boom():
        raise RuntimeError("DB weg")
    monkeypatch.setattr(jobs, "recover_after_restart", boom)
    kern.running.add("s1")
    tick()
    kern.running.discard("s1")
    kern.last_text["s1"] = "x"
    tick()
    assert [t for _, t, _ in kern.commits] == ["x"]
