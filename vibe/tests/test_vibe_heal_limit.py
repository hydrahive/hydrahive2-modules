"""Baustein 6: Kostengrenze des Heilungslaufs (an hydratest 5.11. gefunden).

Die Heilung läuft in der Sitzung des Chats. Der Verbrauch davor gehört nicht zum Lauf: Ein langer Chat darf die Heilung
nicht schon vor Runde 1 sperren (gemessen: Grenze 4000, „letzte Runde“ aus dem Chat 13 426 → Lauf nach 0 Tokens aus).
"""
from __future__ import annotations

from backend import heal_run


def row(p=0, c=0, cc=0, out=0):
    return {"prompt_tokens": p, "cache_read_tokens": c, "cache_creation_tokens": cc, "completion_tokens": out}


def over(rows, before_n, limit):
    return heal_run.over_limit(rows, before_n, limit)


def test_vor_runde_eins_nie_ueber_der_grenze_auch_bei_langem_chat():
    chat = [row(p=90_000, out=3_000)] * 5
    assert over(chat, len(chat), 4_000) is False


def test_nach_runde_eins_zaehlt_nur_der_lauf():
    chat = [row(p=90_000)] * 3
    run1 = [row(p=1_000, out=200)]
    assert over(chat + run1, len(chat), 4_000) is False          # 1 200 + nächste ~1 200 = 2 400 < 4 000


def test_naechste_runde_wird_vorab_mitgerechnet():
    run = [row(p=1_500, out=500), row(p=1_800, out=300)]          # verbraucht 4 100, letzte 2 100
    assert over(run, 0, 6_000) is True                            # 4 100 + 2 100 > 6 000
    assert over(run, 0, 7_000) is False


def test_genau_auf_der_grenze_ist_noch_erlaubt():
    run = [row(p=1_000, out=1_000)]
    assert over(run, 0, 4_000) is False                           # 2 000 + 2 000 == 4 000 → nicht darüber


def test_cache_tokens_zaehlen_mit():
    run = [row(p=100, c=3_000, cc=500, out=100)]
    assert over(run, 0, 3_000) is True                            # 3 700 verbraucht


def test_ohne_grenze_nie():
    assert over([row(p=10**9)], 0, 0) is False


def test_leere_zeilen_und_none_werte():
    assert over([{"prompt_tokens": None, "cache_read_tokens": None, "cache_creation_tokens": None,
                  "completion_tokens": None}], 0, 100) is False


def test_verbrauch_des_laufs_ohne_chat_davor():
    chat = [row(p=50_000)] * 2
    run = [row(p=700, out=100), row(p=900, out=100)]
    assert heal_run.spent(chat + run, len(chat)) == 1_800


# --- Laufende Rückmeldung von `drive` ----------------------------------------------------------------------------

import asyncio                                                    # noqa: E402

import pytest                                                     # noqa: E402


class _Ev:
    def __init__(self, name: str) -> None:
        self.name = name


def _install_core(monkeypatch, *, events, rows_per_round, delay=0.0):
    """Kleine Attrappe des Kerns für `drive`: Ereignisse eines Laufs und die `llm_calls` dazu."""
    import sys
    import types

    rows: list[dict] = []
    ev_mod = types.ModuleType("hydrahive.runner.events")
    ev_mod.IterationStart = type("IterationStart", (), {})
    ev_mod.Done = type("Done", (), {})
    conc = types.ModuleType("hydrahive.runner.concurrency")

    class _Guard:
        async def __aenter__(self):
            return None

        async def __aexit__(self, *a):
            return False
    conc.session_run_guard = lambda sid: _Guard()
    bus_mod = types.ModuleType("hydrahive.runner.event_bus")
    bus_mod.bus = types.SimpleNamespace(open=lambda s: None, close=lambda s: None, publish=lambda s, e: None)
    sse_mod = types.ModuleType("hydrahive.api.routes._sse")
    sse_mod.encode_event = lambda e: ""
    bc_mod = types.ModuleType("hydrahive.api._session_broadcast")
    bc_mod.broadcaster = types.SimpleNamespace(broadcast=lambda s, m: None)
    runner_mod = types.ModuleType("hydrahive.runner")

    async def runner_run(sid, task):
        for kind in events:
            if kind == "iter":
                yield ev_mod.IterationStart()
                rows.append(rows_per_round)
            elif kind == "done":
                yield ev_mod.Done()
            await asyncio.sleep(delay)
    runner_mod.run = runner_run
    for name, mod in {"hydrahive.runner.events": ev_mod, "hydrahive.runner.concurrency": conc,
                      "hydrahive.runner.event_bus": bus_mod, "hydrahive.api.routes._sse": sse_mod,
                      "hydrahive.api._session_broadcast": bc_mod, "hydrahive.runner": runner_mod}.items():
        monkeypatch.setitem(sys.modules, name, mod)
    monkeypatch.setattr(heal_run, "_rows", lambda sid: list(rows))
    return rows


def _row(tokens):
    return {"prompt_tokens": tokens, "cache_read_tokens": 0, "cache_creation_tokens": 0, "completion_tokens": 0}


def test_drive_meldet_limited_wenn_die_grenze_greift(monkeypatch):
    _install_core(monkeypatch, events=["iter", "iter", "iter", "done"], rows_per_round=_row(3_000))
    out = asyncio.run(heal_run.drive("p", "s", "t", limit_tokens=5_000))
    assert out["limited"] is True and out["timed_out"] is False


def test_drive_ohne_grenze_meldet_nicht_limited(monkeypatch):
    _install_core(monkeypatch, events=["iter", "done"], rows_per_round=_row(1_000))
    out = asyncio.run(heal_run.drive("p", "s", "t", limit_tokens=100_000))
    assert out["limited"] is False and out["timed_out"] is False and out["done"] is True


def test_drive_meldet_timed_out_bei_zeitgrenze(monkeypatch):
    monkeypatch.setattr(heal_run, "TIMEOUT_SECONDS", 0.2)
    _install_core(monkeypatch, events=["iter"] * 50, rows_per_round=_row(10), delay=0.1)
    out = asyncio.run(heal_run.drive("p", "s", "t", limit_tokens=10**9))
    assert out["timed_out"] is True and out["limited"] is False and out["done"] is False


def test_drive_wirft_bei_zeitgrenze_nicht(monkeypatch):
    monkeypatch.setattr(heal_run, "TIMEOUT_SECONDS", 0.1)
    _install_core(monkeypatch, events=["iter"] * 50, rows_per_round=_row(10), delay=0.1)
    asyncio.run(heal_run.drive("p", "s", "t", limit_tokens=10**9))        # keine Ausnahme


def test_drive_gibt_verbrauch_auch_bei_zeitgrenze_zurueck(monkeypatch):
    monkeypatch.setattr(heal_run, "TIMEOUT_SECONDS", 0.25)
    _install_core(monkeypatch, events=["iter"] * 50, rows_per_round=_row(100), delay=0.1)
    out = asyncio.run(heal_run.drive("p", "s", "t", limit_tokens=10**9))
    assert out["tokens"] >= 200


def test_drive_schliesst_den_generator_an_der_grenze(monkeypatch):
    closed = {"n": 0}
    rows = _install_core(monkeypatch, events=["iter", "iter", "iter"], rows_per_round=_row(3_000))
    import sys
    orig = sys.modules["hydrahive.runner"].run

    async def tracked(sid, task):
        try:
            async for e in orig(sid, task):
                yield e
        finally:
            closed["n"] += 1
    sys.modules["hydrahive.runner"].run = tracked
    asyncio.run(heal_run.drive("p", "s", "t", limit_tokens=5_000))
    assert closed["n"] == 1 and rows
