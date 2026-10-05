"""Buddy-Werkzeuge fürs Mining: Lesen (buddy_read) und Steuern (hier).

Steuern braucht die Freigabe mining.control. Der Kern entfernt die Werkzeuge
schon für Besitzer ohne Freigabe (Manifest capabilities[].tools); jedes
Werkzeug prüft trotzdem selbst — falls es einem Agenten fest eingetragen wurde.

Bewusst NICHT per Chat: Rechner koppeln, freigeben, sperren, löschen und den
Kryptex-Benutzer (Auszahlungsziel) ändern. Das bleibt der Oberfläche vorbehalten.
"""
from __future__ import annotations

from hydrahive.tools.base import Tool, ToolContext, ToolResult

from . import rigs, runtime_store, store
from .access import CONTROL as CONTROL_CAP
from .buddy_clore import CLORE_DRYRUN
from .buddy_read import BENCHMARKS, EARNINGS, HISTORY, STATUS, ToolInputError, find_rig

ACTIONS = ("on", "off", "rebench", "follow_power", "ignore_power")
SETTABLE = ("switch_threshold", "min_runtime_min", "prop_discount", "region", "power_mode", "power_fixed_w",
            "power_reserve_w", "power_min_minutes")


def _may_control(user: str) -> bool:
    try:
        from hydrahive.access.check import can_use_as
    except ImportError:  # Kern ohne Freigaben-System: Steuern nur für Admins
        from hydrahive.api.middleware.users import get_by_username
        u = get_by_username(user)
        return bool(u and u.get("role") == "admin")
    return can_use_as(user, CONTROL_CAP)


def _denied() -> ToolResult:
    return ToolResult.fail(f"Keine Freigabe „{CONTROL_CAP}“ — Mining steuern darf nur, wer diese Freigabe hat.")


async def _control(args: dict, ctx: ToolContext) -> ToolResult:
    if not _may_control(ctx.user_id):
        return _denied()
    action = args.get("action")
    if action not in ACTIONS:
        return ToolResult.fail(f"action muss eine von {', '.join(ACTIONS)} sein")
    try:
        rig = find_rig(args.get("rig"))
    except ToolInputError as exc:
        return ToolResult.fail(str(exc))
    if rig["status"] != "active":
        return ToolResult.fail(f"Rechner „{rig['name']}“ ist nicht freigegeben — erst in der Oberfläche freigeben.")
    if action in ("on", "off"):
        rigs.set_enabled(rig["id"], action == "on")
        done = "eingeschaltet" if action == "on" else "ausgeschaltet"
    elif action == "rebench":
        runtime_store.clear_bench(rig["id"])
        done = "Messwerte gelöscht — misst beim nächsten Melden neu"
    else:
        rigs.set_power_prefs(rig["id"], action == "follow_power", int(rig.get("priority") or 0))
        done = "folgt jetzt der Energie-Steuerung" if action == "follow_power" else "läuft unabhängig von der Energie"
    return ToolResult.ok({"rig": rig["name"], "action": action, "result": done,
                          "note": "Wirkt beim nächsten Melden des Rechners (spätestens nach ca. 30 s)."})


async def _settings(args: dict, ctx: ToolContext) -> ToolResult:
    changes = args.get("changes") or {}
    if not isinstance(changes, dict):
        return ToolResult.fail("changes muss ein Objekt sein")
    if not changes:
        return ToolResult.ok({"config": store.get_config(), "settable": list(SETTABLE)})
    if not _may_control(ctx.user_id):
        return _denied()
    not_allowed = sorted(set(changes) - set(SETTABLE))
    if not_allowed:
        return ToolResult.fail(f"Nicht per Chat änderbar: {', '.join(not_allowed)} — bitte in der Oberfläche.")
    try:
        cfg = store.update_config(changes)
    except store.ConfigError as exc:
        return ToolResult.fail(f"Ungültiger Wert: {exc}")
    if any(k.startswith("power_") for k in changes):
        from . import power
        power.refresh()
    return ToolResult.ok({"changed": sorted(changes), "config": {k: cfg[k] for k in SETTABLE}})


CONTROL_TOOL = Tool(
    name="mining_rig_control", category="action", execute=_control,
    schema={"type": "object", "required": ["rig", "action"], "properties": {
        "rig": {"type": "string", "description": "Rechner-Name"},
        "action": {"type": "string", "enum": list(ACTIONS),
                   "description": "on/off = ein-/ausschalten, rebench = neu messen, "
                                  "follow_power/ignore_power = Energie-Steuerung folgen oder nicht"}}},
    description="Mining: einen Rechner ein-/ausschalten, neu messen lassen oder an die Energie-Steuerung "
                "koppeln. Braucht die Freigabe mining.control. Koppeln, Freigeben, Sperren und Löschen gehen "
                "nur über die Oberfläche.")
SETTINGS_TOOL = Tool(
    name="mining_settings", category="action", execute=_settings,
    schema={"type": "object", "properties": {"changes": {
        "type": "object", "description": "Zu ändernde Werte; leer = aktuelle Einstellungen anzeigen. Erlaubt: "
        + ", ".join(SETTABLE) + ". Schwelle/Abschlag als Anteil (0.05 = 5 %)."}}, "required": []},
    description="Mining: Einstellungen anzeigen oder ändern (Wechsel-Schwelle, Mindestlaufzeit, Region, "
                "Energie-Steuerung). Ändern braucht die Freigabe mining.control. Den Kryptex-Benutzer "
                "(Auszahlungsziel) ändert nur die Oberfläche.")

CONTROL, SETTINGS = CONTROL_TOOL, SETTINGS_TOOL  # kurze Namen; die Freigabe heißt hier CONTROL_CAP
TOOLS = (STATUS, EARNINGS, HISTORY, BENCHMARKS, CLORE_DRYRUN, CONTROL_TOOL, SETTINGS_TOOL)
