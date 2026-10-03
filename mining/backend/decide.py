"""Entscheider: Was soll ein Rig jetzt tun? Reine Funktionen, kein I/O.

Reihenfolge je Rig:
1. nicht freigegeben / ausgeschaltet / kein Kryptex-Benutzer → stop
2. Energie-Steuerung sagt aus → stop (E5, kommt als ``power_ok=False``)
3. Benchmark offen (Coin×Miner ohne Messung) → benchmark dieses Paars
4. bester Coin aus eigener Messung × Live-Ertrag → mine
   Wechsel nur, wenn neuer Ertrag ≥ (1 + Schwelle) × aktueller UND der
   aktuelle seit ≥ Mindestlaufzeit läuft. Fällt der aktuelle Coin weg
   (kein Kurs mehr, Fehler), sofort wechseln.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from . import catalog
from .profit import CoinQuote, usd_per_day

BENCH_MAX_FAILURES = 1  # ein fehlgeschlagener Lauf reicht: Paar wird übersprungen


@dataclass(frozen=True)
class Assignment:
    mode: str                 # mine | benchmark | stop
    coin: str | None = None
    miner: str | None = None
    algo: str | None = None
    reason: str = ""


def pending_benchmarks(vendor: str, done: set[tuple[str, str]], quotes: dict[str, CoinQuote]) -> list[tuple[str, str, str]]:
    """(coin, miner, algo) ohne Messung — nur Coins, die Kryptex gerade anbietet."""
    out = []
    for coin in catalog.coins():
        if coin not in quotes:
            continue
        for miner, algo in catalog.options(coin, vendor):
            if (coin, miner) not in done:
                out.append((coin, miner, algo))
    return out


def best_option(bench: dict[tuple[str, str], float], quotes: dict[str, CoinQuote], vendor: str,
                prop_discount: float) -> tuple[str, str, str, float] | None:
    """(coin, miner, algo, usd/Tag) mit dem höchsten Ertrag aus eigenen Messungen."""
    best = None
    for coin, q in quotes.items():
        for miner, algo in catalog.options(coin, vendor):
            hr = bench.get((coin, miner))
            if not hr:
                continue
            usd = usd_per_day(q, hr, prop_discount=prop_discount)
            if usd is not None and (best is None or usd > best[3]):
                best = (coin, miner, algo, usd)
    return best


def current_value(cur: Assignment | None, bench: dict[tuple[str, str], float], quotes: dict[str, CoinQuote],
                  prop_discount: float) -> float | None:
    if not cur or cur.mode != "mine" or cur.coin not in quotes:
        return None
    hr = bench.get((cur.coin, cur.miner or ""))
    return usd_per_day(quotes[cur.coin], hr, prop_discount=prop_discount) if hr else None


def decide(*, rig: dict, cfg: dict, quotes: dict[str, CoinQuote], bench: dict[tuple[str, str], float],
           failed: set[tuple[str, str]], current: Assignment | None, current_since: datetime | None,
           now: datetime, power_ok: bool = True, power_reason: str = "power_budget") -> Assignment:
    if rig.get("status") != "active":
        return Assignment("stop", reason="awaiting_approval")
    if not rig.get("enabled"):
        return Assignment("stop", reason="disabled")
    if not cfg.get("kryptex_user"):
        return Assignment("stop", reason="no_kryptex_user")
    vendor = rig.get("gpu_vendor") or ""
    if vendor not in ("nvidia", "amd"):
        return Assignment("stop", reason="no_supported_gpu")
    if not power_ok:
        return Assignment("stop", reason=power_reason)
    todo = pending_benchmarks(vendor, set(bench) | failed, quotes)
    if todo:
        coin, miner, algo = todo[0]
        return Assignment("benchmark", coin, miner, algo, reason=f"benchmark {len(todo)} offen")
    best = best_option(bench, quotes, vendor, cfg.get("prop_discount", 0.0))
    if best is None:
        return Assignment("stop", reason="no_profitable_option")
    coin, miner, algo, usd = best
    cur_usd = current_value(current, bench, quotes, cfg.get("prop_discount", 0.0))
    if cur_usd is not None and current is not None and (current.coin, current.miner) != (coin, miner):
        min_run = timedelta(minutes=cfg.get("min_runtime_min", 15))
        too_soon = current_since is not None and now - current_since < min_run
        not_enough = usd < cur_usd * (1 + cfg.get("switch_threshold", 0.05))
        if too_soon or not_enough:
            return Assignment("mine", current.coin, current.miner, current.algo,
                              reason="keep (too_soon)" if too_soon else "keep (below_threshold)")
    return Assignment("mine", coin, miner, algo, reason=f"best {usd:.3f} usd/day")
