"""Energie-Steuerung: Wie viele Rigs dürfen gerade laufen? (Spec §E5)

- ``power_mode = off`` (Standard): Energie spielt keine Rolle, alle laufen.
- sonst: Budget = verfügbare Watt − Reserve. Rigs, die der Steuerung folgen,
  werden nach Priorität, dann nach Ertrag je Watt sortiert und eingeschaltet,
  solange ihr Verbrauch ins Budget passt. Rigs mit ``follows_power = 0``
  laufen immer (zählen aber gegen das Budget).
- Gegen Flattern: ein Rig bleibt mindestens ``power_min_minutes`` an bzw. aus.
- Quelle nicht erreichbar (``None``) seit > ``power_stale_minutes`` → alle
  folgenden Rigs aus (sonst würde ohne PV Netzstrom verbraucht).

Die Quelle wird im Hintergrundjob gelesen (``refresh``), die Verteilung bei
jeder Rig-Meldung aus dem Zwischenstand gerechnet (``allowed``).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from . import power_source, runtime_store, store

logger = logging.getLogger(__name__)
DEFAULT_RIG_WATTS = 200.0
_state: dict = {"watts": None, "ok_at": None}


def refresh() -> None:
    """Quelle lesen (Hintergrundjob, alle 30 s)."""
    src = power_source.from_config(store.get_config())
    if src is None:
        _state.update(watts=None, ok_at=None)
        return
    w = src.available_watts()
    if w is not None:
        _state.update(watts=w, ok_at=datetime.now(timezone.utc))


def rig_watts(rig: dict) -> float:
    """Gemessene Watt des ganzen Rigs; unbekannt/Leerlauf → Schätzung je Karte."""
    rep = rig.get("last_report_obj") or {}
    cards = rep.get("gpu_count")
    cards = int(cards) if isinstance(cards, int) and not isinstance(cards, bool) and 1 <= cards <= 64 else 1
    w = rep.get("power_w")
    return float(w) if isinstance(w, (int, float)) and w > 30 * cards else DEFAULT_RIG_WATTS * cards


def plan(rigs: list[dict], budget: float) -> set[str]:
    """IDs der Rigs, die laufen dürfen (reine Funktion)."""
    budget -= sum(rig_watts(r) for r in rigs if not r.get("follows_power"))
    allowed = {r["id"] for r in rigs if not r.get("follows_power")}
    followers = sorted((r for r in rigs if r.get("follows_power")),
                       key=lambda r: (-int(r.get("priority") or 0), -(r.get("_value_per_watt") or 0), r["name"]))
    for r in followers:
        need = rig_watts(r)
        if need <= budget:
            allowed.add(r["id"])
            budget -= need
    return allowed


OFF_BUDGET = "power_budget"
OFF_NO_DATA = "power_source_down"
OFF_REASONS = (OFF_BUDGET, OFF_NO_DATA)


def allowed(rig: dict, *, now: datetime, state_key: str | None = None) -> tuple[bool, bool, str]:
    """(darf laufen, Energie-Zustand hat sich geändert, Grund falls aus).

    Mindestzeit gilt nur für Budget-Wechsel (gegen Flattern bei Wolken).
    War der Rig nur aus, weil die Quelle fehlte, geht er sofort wieder an,
    sobald Werte da sind.
    """
    cfg = store.get_config()
    if cfg.get("power_mode", "off") == "off" or not rig.get("follows_power"):
        return True, False, ""
    stale = _state["ok_at"] is None or now - _state["ok_at"] > timedelta(minutes=cfg.get("power_stale_minutes", 15))
    if stale:
        want, reason = False, OFF_NO_DATA
    else:
        from .rigs import active_rigs_for_power
        budget = (_state["watts"] or 0) - cfg.get("power_reserve_w", 100)
        want, reason = rig["id"] in plan(active_rigs_for_power(), budget), OFF_BUDGET
    # Energy switches the whole rig; its state lives in the assignment of the first group.
    cur, _, power_since = runtime_store.get_assignment(state_key or rig["id"])
    was_on = cur is not None and cur.reason not in OFF_REASONS
    came_from_no_data = cur is not None and cur.reason == OFF_NO_DATA
    if (cur is not None and want != was_on and power_since is not None and not stale and not came_from_no_data
            and now - power_since < timedelta(minutes=cfg.get("power_min_minutes", 10))):
        return was_on, False, OFF_BUDGET          # Mindestzeit noch nicht um → Zustand halten
    return want, (cur is None) or (want != was_on), reason


def status() -> dict:
    cfg = store.get_config()
    return {"mode": cfg.get("power_mode", "off"), "available_w": _state["watts"],
            "ok_at": _state["ok_at"].isoformat() if _state["ok_at"] else None,
            "reserve_w": cfg.get("power_reserve_w", 100)}
