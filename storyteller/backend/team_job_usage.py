"""Verbrauch eines Team-Auftrags aus der Kern-Tabelle ``llm_calls`` (A1, Spec kostengrenze.md §4).

Der Kern-Runner schreibt je Modellaufruf eine Zeile (echte Zahlen inkl. Cache). Daraus: Summe für Grenze und Kosten
(auch bei Abbruch, Fehler, Zeitgrenze – dann gibt es kein ``Done``) und der Verbrauch der letzten Runde als Schätzung
für die nächste (der Verlauf wächst, die nächste Runde ist mindestens so groß).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Usage:
    tokens_in: int        # Eingabe inkl. Cache-Lesen/-Schreiben (wie bei „done“)
    tokens_out: int
    last: int             # Eingabe + Ausgabe des letzten Modellaufrufs
    cost_micros: int | None

    @property
    def total(self) -> int:
        return self.tokens_in + self.tokens_out


def _n(v) -> int:
    return int(v or 0)


def of_session(session_id: str) -> Usage:
    from hydrahive.db import llm_calls
    rows = llm_calls.for_session(session_id) if session_id else []
    tin = tout = last = 0
    costs: list[int | None] = []
    for r in rows:
        r_in = _n(r["prompt_tokens"]) + _n(r["cache_read_tokens"]) + _n(r["cache_creation_tokens"])
        r_out = _n(r["completion_tokens"])
        tin, tout, last = tin + r_in, tout + r_out, r_in + r_out
        costs.append(r["cost_micros"])
    known = [c for c in costs if c is not None]
    return Usage(tin, tout, last, sum(known) if known else None)
