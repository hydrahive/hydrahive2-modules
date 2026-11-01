"""Störungen als Zeiträume: aus Ereignissen der Dream Machine und aus der eigenen Minuten-Messung.

Arten: wan (Dream Machine: Internet weg, mit Dauer), blip (kurzer Aussetzer laut Dream Machine),
internet (eigene Messung: gar kein Internet), cable (eigene Messung: kein Kabel – Internet weg ODER Mobilfunk-Ersatz).
"""
from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

STEP = 60          # eine Messung je Minute
_GAP = 2 * STEP    # mehr Abstand = Lücke in der Messung → Zeitraum endet


def from_udm(events: list[dict]) -> list[dict]:
    out = []
    for e in events:
        kind = {"wan_restored": "wan", "wan_blip": "blip"}.get(e["kind"])
        if kind and e.get("duration_s"):
            out.append({"start": e["ts"] - e["duration_s"], "end": e["ts"], "kind": kind, "source": "udm"})
    return out


def _runs(samples: list[dict], bad: set[str], kind: str) -> list[dict]:
    out: list[dict] = []
    cur: dict | None = None
    last = None
    for s in sorted(samples, key=lambda x: x["ts"]):
        if cur and last is not None and s["ts"] - last > _GAP:
            out.append(cur)
            cur = None
        if s["path"] in bad:
            if cur is None:
                cur = {"start": s["ts"], "end": s["ts"] + STEP, "kind": kind, "source": "probe"}
            cur["end"] = s["ts"] + STEP
        elif cur:
            out.append(cur)
            cur = None
        last = s["ts"]
    if cur:
        out.append(cur)
    return out


def from_samples(samples: list[dict]) -> list[dict]:
    return _runs(samples, {"none"}, "internet") + _runs(samples, {"none", "mobile"}, "cable")


def merge(items: list[dict]) -> list[dict]:
    """Überlappende Zeiträume gleicher Art und Quelle zusammenfassen."""
    out: list[dict] = []
    for o in sorted(items, key=lambda x: (x["kind"], x["source"], x["start"])):
        prev = out[-1] if out else None
        if prev and prev["kind"] == o["kind"] and prev["source"] == o["source"] and o["start"] <= prev["end"]:
            prev["end"] = max(prev["end"], o["end"])
        else:
            out.append(dict(o))
    return out


def per_day(items: list[dict], kind: str, tz: ZoneInfo) -> dict[str, int]:
    """Sekunden je Kalendertag (Ortszeit) für eine Art; Zeiträume über Mitternacht werden aufgeteilt."""
    out: dict[str, int] = {}
    for o in items:
        if o["kind"] != kind:
            continue
        t = o["start"]
        while t < o["end"]:
            day = datetime.fromtimestamp(t, tz).date()
            nxt = int(datetime.combine(day + timedelta(days=1), datetime.min.time(), tz).timestamp())
            end = min(o["end"], nxt)
            out[day.isoformat()] = out.get(day.isoformat(), 0) + end - t
            t = end
    return out
