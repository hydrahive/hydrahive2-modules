"""Laufzeit-Speicher: Messungen, Zuteilungen, Wechsel-Protokoll."""
from __future__ import annotations

from datetime import datetime, timezone

from hydrahive.db.connection import db

from .decide import Assignment

MAX_LOG_PER_RIG = 200


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# Rechner + alle seine Hersteller-Gruppen (Schlüssel "<rig_id>#<hersteller>"); substr statt LIKE (_ ist Joker).
_ALL_KEYS = "(rig_id = ? OR substr(rig_id, 1, ?) = ?)"


def _all(rig_id: str) -> tuple:
    return (rig_id, len(rig_id) + 1, rig_id + "#")


def bench_for(rig_id: str) -> tuple[dict[tuple[str, str], float], set[tuple[str, str]]]:
    """({(coin, miner): H/s}, {(coin, miner) fehlgeschlagen})."""
    with db() as c:
        rows = c.execute("SELECT coin, miner, hashrate FROM module_mining_benchmarks WHERE rig_id = ?",
                         (rig_id,)).fetchall()
    ok = {(r["coin"], r["miner"]): r["hashrate"] for r in rows if r["hashrate"]}
    failed = {(r["coin"], r["miner"]) for r in rows if not r["hashrate"]}
    return ok, failed


def save_bench(rig_id: str, coin: str, miner: str, algo: str, hashrate: float | None,
               watts: float | None, error: str | None) -> None:
    with db() as c:
        c.execute(
            "INSERT INTO module_mining_benchmarks (rig_id, coin, miner, algo, hashrate, watts, error, measured_at)"
            " VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(rig_id, coin, miner) DO UPDATE SET algo=excluded.algo,"
            " hashrate=excluded.hashrate, watts=excluded.watts, error=excluded.error, measured_at=excluded.measured_at",
            (rig_id, coin, miner, algo, hashrate if hashrate and hashrate > 0 else None, watts,
             (error or "")[:200] or None, _now()),
        )


def list_bench(rig_id: str) -> list[dict]:
    """Messungen des Rechners samt aller Hersteller-Gruppen; ``vendor`` nur bei gemischten Rechnern."""
    with db() as c:
        rows = [dict(r) for r in c.execute(
            "SELECT rig_id, coin, miner, algo, hashrate, watts, error, measured_at FROM module_mining_benchmarks"
            f" WHERE {_ALL_KEYS} ORDER BY coin, miner", _all(rig_id))]
    for r in rows:
        key = r.pop("rig_id")
        r["vendor"] = key.split("#", 1)[1] if "#" in key else None
    return rows


def clear_bench(rig_id: str) -> None:
    with db() as c:
        c.execute(f"DELETE FROM module_mining_benchmarks WHERE {_ALL_KEYS}", _all(rig_id))


def get_assignment(rig_id: str) -> tuple[Assignment | None, datetime | None, datetime | None]:
    """(Zuteilung, seit, Energie-Zustand seit)."""
    with db() as c:
        r = c.execute("SELECT * FROM module_mining_assignments WHERE rig_id = ?", (rig_id,)).fetchone()
    if not r:
        return None, None, None
    a = Assignment(r["mode"], r["coin"], r["miner"], r["algo"], r["reason"] or "")
    ps = datetime.fromisoformat(r["power_since"]) if r["power_since"] else None
    return a, datetime.fromisoformat(r["since"]), ps


def set_assignment(rig_id: str, new: Assignment, old: Assignment | None, *, power_changed: bool) -> None:
    """Zuteilung speichern. ``since`` springt nur bei echtem Wechsel; Wechsel → Protokoll."""
    changed = old is None or (old.mode, old.coin, old.miner) != (new.mode, new.coin, new.miner)
    now = _now()
    with db() as c:
        c.execute(
            "INSERT INTO module_mining_assignments (rig_id, mode, coin, miner, algo, reason, since, power_since)"
            " VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(rig_id) DO UPDATE SET mode=excluded.mode, coin=excluded.coin,"
            " miner=excluded.miner, algo=excluded.algo, reason=excluded.reason,"
            " since=CASE WHEN ? THEN excluded.since ELSE since END,"
            " power_since=CASE WHEN ? THEN excluded.power_since ELSE COALESCE(power_since, excluded.power_since) END",
            (rig_id, new.mode, new.coin, new.miner, new.algo, new.reason, now, now, int(changed), int(power_changed)),
        )
        if changed:
            c.execute("INSERT INTO module_mining_switch_log (rig_id, from_coin, to_coin, reason, at) VALUES (?,?,?,?,?)",
                      (rig_id, f"{old.mode}:{old.coin or '-'}" if old else None,
                       f"{new.mode}:{new.coin or '-'}", new.reason[:120], now))
            c.execute("DELETE FROM module_mining_switch_log WHERE rig_id = ? AND id NOT IN (SELECT id FROM"
                      " module_mining_switch_log WHERE rig_id = ? ORDER BY id DESC LIMIT ?)",
                      (rig_id, rig_id, MAX_LOG_PER_RIG))


def switch_log(rig_id: str | None = None, limit: int = 50) -> list[dict]:
    q = "SELECT rig_id, from_coin, to_coin, reason, at FROM module_mining_switch_log"
    args: tuple = ()
    if rig_id:
        q += f" WHERE {_ALL_KEYS}"
        args = _all(rig_id)
    with db() as c:
        return [dict(r) for r in c.execute(q + " ORDER BY id DESC LIMIT ?", (*args, limit))]


def forget_rig(rig_id: str) -> None:
    with db() as c:
        for t in ("module_mining_benchmarks", "module_mining_assignments", "module_mining_switch_log",
                  "module_mining_samples"):
            c.execute(f"DELETE FROM {t} WHERE {_ALL_KEYS}", _all(rig_id))
