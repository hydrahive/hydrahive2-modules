"""A4-Messung (kein normaler Test, Name ohne test_-Präfix): Buch mit N Szenen, Zeiten und Dateizugriffe.

Aufruf:  python -m pytest -q -s tests/perf_a4_probe.py -p no:cacheprovider   (PERF_SCENES=500 Standard)
"""
from __future__ import annotations

import asyncio
import builtins
import os
import time
from pathlib import Path

from conftest import PROJECT_ID

from backend import ghost, run_engine, run_plan, runs, storage

N = int(os.environ.get("PERF_SCENES", "500"))
WORDS = 1500


class _Opens:
    """Zählt Dateiöffnungen (open + Path.read_text) – grob, aber vorher/nachher vergleichbar."""
    def __enter__(self):
        self.n = 0
        self._open, self._rt = builtins.open, Path.read_text
        me = self

        def op(*a, **k):
            me.n += 1
            return me._open(*a, **k)

        def rt(self_, *a, **k):
            me.n += 1
            return me._rt(self_, *a, **k)
        builtins.open, Path.read_text = op, rt
        return self

    def __exit__(self, *exc):
        builtins.open, Path.read_text = self._open, self._rt


def _book(n: int) -> tuple[str, list[str]]:
    b = storage.create_book(PROJECT_ID, {"title": f"Perf {n}", "kind": "novel", "language": "de"})
    st = storage.get_structure(PROJECT_ID, b["id"])
    first = st["parts"][0]["chapters"][0]
    sids = [first["scenes"][0]]
    chapter = first["id"]
    text = ("Mia ging zum Hafen und sah das Lotsenboot. " * (WORDS // 8)).strip()
    for i in range(1, n):
        if i % 20 == 0:
            chapter = storage.add_chapter(PROJECT_ID, b["id"], st["parts"][0]["id"], f"Kapitel {i // 20 + 1}", "S")["scene"]
            sids.append(chapter["id"])
            chapter = next(c for p in storage.get_structure(PROJECT_ID, b["id"])["parts"] for c in p["chapters"] if chapter["id"] in c["scenes"])["id"]
            continue
        sids.append(storage.add_scene(PROJECT_ID, b["id"], chapter, f"S{i}", after=sids[-1])["scene"]["id"])
    for sid in sids:
        s = storage.get_scene(PROJECT_ID, b["id"], sid)
        storage.save_scene(PROJECT_ID, b["id"], sid, {"text": text, "summary": f"In Szene {sid[:6]} passiert etwas."},
                           base_version=s["version"])
    storage.update_book(PROJECT_ID, b["id"], {"ghost": {"length_words": 300}}, base_version=storage.get_book(PROJECT_ID, b["id"])["version"])
    return b["id"], sids


def _t(fn, *a, **k):
    with _Opens() as o:
        t0 = time.perf_counter()
        out = fn(*a, **k)
        dt = time.perf_counter() - t0
    return out, dt, o.n


def test_probe(setup_test_env, monkeypatch):
    bid, sids = _book(N)
    print(f"\n=== Buch mit {len(sids)} Szenen à {WORDS} Wörtern")
    _, dt, n = _t(storage.list_books, PROJECT_ID)
    print(f"list_books (Bücherliste)            {dt * 1000:8.1f} ms  {n:6d} Dateien")
    run_set = sids[-200:]                      # ein Lauf umfasst höchstens 200 Szenen (MAX_RUN_SCENES)
    _, dt, n = _t(run_plan.plan, PROJECT_ID, bid, scope="from", scene_id=run_set[0], skip_filled=False)
    print(f"run_plan letzte 200 (Schätzung)      {dt * 1000:8.1f} ms  {n:6d} Dateien")
    _, dt, n = _t(ghost.build_material, PROJECT_ID, bid, sids[-1])
    print(f"build_material letzte Szene          {dt * 1000:8.1f} ms  {n:6d} Dateien")

    # Buchlauf ohne Modell: nur Material + Ablegen je Szene; dazu: wie lange blockiert die Ereignisschleife am Stück?
    async def fake_stream(messages, model=None, temperature=0.7, max_tokens=4096):
        await asyncio.sleep(0.01)          # wie ein echter Netzaufruf: gibt die Ereignisschleife kurz frei
        yield "Text " * 10
    monkeypatch.setattr(ghost, "stream", fake_stream)
    run = runs.create_run(user="testuser", project_id=PROJECT_ID, book_id=bid, scope="from", scene_ids=run_set,
                          model="m", options={"skip_filled": False, "length_words": 300})

    async def main():
        gaps, last, stop = [], time.perf_counter(), False
        start = last
        where: list = []

        async def ticker():
            nonlocal last
            while not stop:
                await asyncio.sleep(0.005)
                now = time.perf_counter()
                gaps.append(now - last)
                if now - last > 0.05:
                    where.append((round((now - last) * 1000), round(last - start, 2)))
                last = now
        tick = asyncio.create_task(ticker())
        t0 = time.perf_counter()
        with _Opens() as o:
            await run_engine.execute(run["id"], PROJECT_ID, bid, "testuser")
        dt = time.perf_counter() - t0
        stop = True
        await tick
        gaps = gaps or [dt]
        print(f"  Pausen > 50 ms (ms, Sekunde ab Start): {sorted(where, reverse=True)[:8]}  von {len(gaps)}")
        return dt, o.n, max(gaps), sorted(gaps)[int(len(gaps) * 0.99)]
    dt, n, worst, p99 = asyncio.run(main())
    print(f"Lauf letzte {len(run_set)} Szenen (Modell gefälscht) {dt:8.1f} s   {n:6d} Dateien")
    print(f"  Ereignisschleife blockiert: längste Pause {worst * 1000:.0f} ms, 99 % unter {p99 * 1000:.0f} ms")
    print(f"  Status: {runs.get_run(PROJECT_ID, bid, run['id'])['status']}")
