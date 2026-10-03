"""Buddy-Werkzeuge zum Lesen: Zustand, Erträge, Verlauf, Messungen.

Rechte: Grundfreigabe module.mining (Kern filtert Werkzeuge nach Freigaben des
Besitzers). Keine Geheimnisse in der Ausgabe (kein Token, kein Kopplungscode).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from hydrahive.tools.base import Tool, ToolContext, ToolResult

from . import history, rigs, runtime_store, store
from .profit import usd_per_day

OFFLINE_AFTER = timedelta(minutes=2)
_HOURS = {"type": "integer", "minimum": 1, "maximum": 168, "description": "Zeitraum in Stunden (1–168), Standard 24"}
_RIG = {"type": "string", "description": "Rechner-Name (wie in der Liste, z. B. rig-01)"}


class ToolInputError(ValueError):
    pass


def hours_arg(args: dict, default: int = 24) -> int:
    h = args.get("hours", default)
    if isinstance(h, bool) or not isinstance(h, int) or not 1 <= h <= 168:
        raise ToolInputError("hours muss eine ganze Zahl von 1 bis 168 sein")
    return h


def find_rig(name: object) -> dict:
    if not isinstance(name, str) or not name:
        raise ToolInputError("rig fehlt (Rechner-Name)")
    for r in rigs.list_rigs():
        if r["name"] == name and r["status"] != "revoked":
            return r
    raise ToolInputError(f"Rechner „{name}“ nicht gefunden")


def _state(r: dict, now: datetime) -> str:
    if r["status"] != "active":
        return "wartet auf Freigabe" if r["status"] == "pending" else r["status"]
    if not r["enabled"]:
        return "ausgeschaltet"
    seen = datetime.fromisoformat(r["last_seen"]) if r.get("last_seen") else None
    return "online" if seen and now - seen <= OFFLINE_AFTER else "offline"


def _activity(r: dict) -> str:
    a = r.get("assignment") or {}
    if a.get("mode") == "mine":
        return f"schürft {str(a.get('coin')).upper()} ({a.get('miner')})"
    if a.get("mode") == "benchmark":
        done = r["bench_done"] + r["bench_failed"]
        return f"Benchmark {done}/{r['bench_total']}: {str(a.get('coin')).upper()} ({a.get('miner')})"
    return f"angehalten ({a.get('reason') or '—'})"


def _rig_line(r: dict, now: datetime) -> dict:
    rep = r.get("last_report") or {}
    return {"name": r["name"], "state": _state(r, now), "activity": _activity(r),
            "gpu": r.get("gpu_model"), "cards": rep.get("gpu_count"), "hashrate": rep.get("hashrate"),
            "power_w": rep.get("power_w"), "temp_c": rep.get("temp_c"), "error": rep.get("error"),
            "last_seen": r.get("last_seen"), "client_version": r.get("client_version")}


async def _status(args: dict, ctx: ToolContext) -> ToolResult:
    now = datetime.now(timezone.utc)
    lines = [_rig_line(r, now) for r in rigs.list_rigs() if r["status"] != "revoked"]
    states = [x["state"] for x in lines]
    summary = {"total": len(lines), "online": states.count("online"), "offline": states.count("offline"),
               "mining": sum(x["activity"].startswith("schürft") for x in lines),
               "benchmark": sum(x["activity"].startswith("Benchmark") for x in lines)}
    cfg = store.get_config()
    return ToolResult.ok({"summary": summary, "rigs": lines,
                          "power_mode": cfg.get("power_mode"), "kryptex_user_set": bool(cfg.get("kryptex_user"))})


async def _earnings(args: dict, ctx: ToolContext) -> ToolResult:
    try:
        hours = hours_arg(args)
    except ToolInputError as exc:
        return ToolResult.fail(str(exc))
    rate = store.get_usd_per_eur()
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    by_rig, now_total = [], 0.0
    for r in rigs.list_rigs():
        if r["status"] == "revoked":
            continue
        pts = [p for p in history.points(r["id"], since=since) if p["usd_day"] is not None]
        avg = sum(p["usd_day"] for p in pts) / len(pts) if pts else None
        last = pts[-1]["usd_day"] if pts else None
        now_total += last or 0.0
        by_rig.append({"name": r["name"], "now_eur_day": last / rate if last is not None and rate else None,
                       "avg_eur_day": avg / rate if avg is not None and rate else None,
                       "mining_minutes": len(pts)})
    return ToolResult.ok({"hours": hours, "currency": "EUR", "usd_per_eur": rate,
                          "now_eur_day": now_total / rate if rate else None, "by_rig": by_rig,
                          "note": "Schätzung aus Hashrate × Kryptex-Ertrag zum jeweiligen Zeitpunkt, keine Auszahlung."})


async def _history(args: dict, ctx: ToolContext) -> ToolResult:
    try:
        rig, hours = find_rig(args.get("rig")), hours_arg(args)
    except ToolInputError as exc:
        return ToolResult.fail(str(exc))
    pts = history.downsample(history.points(rig["id"], since=datetime.now(timezone.utc) - timedelta(hours=hours)), 48)
    return ToolResult.ok({"rig": rig["name"], "hours": hours, "points": pts,
                          "switches": runtime_store.switch_log(rig["id"], limit=20)})


async def _benchmarks(args: dict, ctx: ToolContext) -> ToolResult:
    try:
        rig = find_rig(args.get("rig"))
    except ToolInputError as exc:
        return ToolResult.fail(str(exc))
    quotes = {q.coin: q for q in store.load_quotes()[0]}
    rate, discount = store.get_usd_per_eur(), store.get_config().get("prop_discount", 0.0)
    measured, failed = [], []
    for b in runtime_store.list_bench(rig["id"]):
        if not b.get("hashrate"):
            failed.append({"coin": b["coin"], "miner": b["miner"], "error": b.get("error")})
            continue
        q = quotes.get(b["coin"])
        usd = usd_per_day(q, b["hashrate"], prop_discount=discount) if q else None
        measured.append({"coin": b["coin"], "miner": b["miner"], "hashrate": b["hashrate"], "watts": b.get("watts"),
                         "eur_day": usd / rate if usd is not None and rate else None})
    measured.sort(key=lambda x: x["eur_day"] or 0, reverse=True)
    return ToolResult.ok({"rig": rig["name"], "measured": measured, "failed": failed,
                          "open": max(0, rig["bench_total"] - len(measured) - len(failed))})


STATUS = Tool(name="mining_status", category="data", execute=_status,
              schema={"type": "object", "properties": {}, "required": []},
              description="Mining: Überblick über alle Rechner (online/offline/aus, was sie gerade tun, Karte, "
                          "Watt, Temperatur, letzter Fehler). Erste Wahl bei Fragen wie „Wie läuft das Mining?“.")
EARNINGS = Tool(name="mining_earnings", category="data", execute=_earnings,
                schema={"type": "object", "properties": {"hours": _HOURS}, "required": []},
                description="Mining: geschätzter Ertrag in €/Tag — jetzt und im Schnitt über einen Zeitraum, "
                            "je Rechner und gesamt.")
HISTORY = Tool(name="mining_rig_history", category="data", execute=_history,
               schema={"type": "object", "properties": {"rig": _RIG, "hours": _HOURS}, "required": ["rig"]},
               description="Mining: Verlauf eines Rechners (Ertrag, Leistung % vom Benchmark, Watt/Temperatur je "
                           "Karte, Coin-Wechsel). Für Auswertungen und Fehlersuche.")
BENCHMARKS = Tool(name="mining_benchmarks", category="data", execute=_benchmarks,
                  schema={"type": "object", "properties": {"rig": _RIG}, "required": ["rig"]},
                  description="Mining: gemessene Hashraten eines Rechners je Coin/Miner, nach aktuellem Ertrag "
                              "sortiert, plus fehlgeschlagene und offene Messungen.")
