"""Home-Assistant-Lese-Tools — ha_list_entities, ha_get_state, ha_render_template.

Lassen den Agenten den HA-Zustand abfragen, ohne etwas zu schalten. Alle Calls
gehen durch den client (URL+Token aus Settings). Eingaben werden validiert,
bevor sie in Upstream-URLs fließen.
"""
from __future__ import annotations

from hydrahive.tools.base import Tool, ToolContext, ToolResult

from . import client, validators

_MAX_LIST = 200


# --------------------------------------------------------------------------- #
# ha_list_entities
# --------------------------------------------------------------------------- #
_LIST_DESC = (
    "Listet Home-Assistant-Entities (Geräte, Sensoren, Schalter, Lampen …) mit "
    "ihrem aktuellen Zustand. Optional nach Domain filtern (z.B. 'light', "
    "'switch', 'sensor', 'climate') oder per Freitext ('wohnzimmer', 'temperatur'). "
    "Nutze dies für Fragen wie 'Welche Lampen gibt es?' oder 'Zeig mir alle Sensoren'."
)

_LIST_SCHEMA = {
    "type": "object",
    "properties": {
        "domain": {
            "type": "string",
            "description": "Optional: nur diese HA-Domain, z.B. 'light', 'switch', 'sensor', 'climate'.",
        },
        "search": {
            "type": "string",
            "description": "Optional: Freitext-Filter über Name und entity_id (z.B. 'wohnzimmer').",
        },
    },
}


def _matches(row: dict, domain: str, search: str) -> bool:
    if domain and row.get("domain") != domain:
        return False
    if search:
        hay = f"{row.get('entity_id', '')} {row.get('name', '')}".lower()
        if search not in hay:
            return False
    return True


def _fmt_row(r: dict) -> str:
    unit = f" {r['unit']}" if r.get("unit") else ""
    return f"{r.get('name')} [{r.get('entity_id')}] = {r.get('state')}{unit}"


async def _list_entities(args: dict, ctx: ToolContext) -> ToolResult:
    domain = (args.get("domain") or "").strip().lower()
    if domain and not validators.is_domain(domain):
        return ToolResult.fail("Ungültige Domain (nur Kleinbuchstaben/Ziffern/_).")
    search = (args.get("search") or "").strip().lower()

    try:
        rows = await client.states()
    except client.HAConfigError as exc:
        return ToolResult.fail(str(exc))
    except client.HAError as exc:
        return ToolResult.fail(str(exc))

    hits = [r for r in rows if _matches(r, domain, search)]
    hits.sort(key=lambda r: (r.get("domain") or "", r.get("name") or ""))
    total = len(hits)
    hits = hits[:_MAX_LIST]
    if not hits:
        return ToolResult.ok({"count": 0, "message": "Keine passenden Entities gefunden."})
    lines = [_fmt_row(r) for r in hits]
    return ToolResult.ok({
        "count": total,
        "shown": len(hits),
        "data": "\n".join(lines),
    })


# --------------------------------------------------------------------------- #
# ha_get_state
# --------------------------------------------------------------------------- #
_STATE_DESC = (
    "Liest den aktuellen Zustand und die Attribute einer einzelnen "
    "Home-Assistant-Entity. Nutze dies für 'Wie warm ist es im Wohnzimmer?' "
    "(entity_id z.B. 'sensor.wohnzimmer_temperatur') oder 'Ist die Lampe an?'."
)

_STATE_SCHEMA = {
    "type": "object",
    "properties": {
        "entity_id": {
            "type": "string",
            "description": "Volle entity_id, z.B. 'light.wohnzimmer' oder 'sensor.bad_temperatur'.",
        },
    },
    "required": ["entity_id"],
}


async def _get_state(args: dict, ctx: ToolContext) -> ToolResult:
    entity_id = (args.get("entity_id") or "").strip().lower()
    if not validators.is_entity(entity_id):
        return ToolResult.fail("Ungültige entity_id (Format: domain.objekt, z.B. light.wohnzimmer).")

    try:
        s = await client.state(entity_id)
    except client.HAConfigError as exc:
        return ToolResult.fail(str(exc))
    except client.HAError as exc:
        return ToolResult.fail(str(exc))

    unit = f" {s['unit']}" if s.get("unit") else ""
    attrs = s.get("attributes") or {}
    # Nur die nützlichsten Attribute kompakt mitgeben.
    keys = [k for k in ("friendly_name", "device_class", "brightness", "temperature",
                        "current_temperature", "hvac_action", "battery_level") if k in attrs]
    attr_str = ", ".join(f"{k}={attrs[k]}" for k in keys)
    summary = f"{s.get('name')} [{entity_id}] = {s.get('state')}{unit}"
    if attr_str:
        summary += f" ({attr_str})"
    return ToolResult.ok({"summary": summary, "state": s.get("state"), "attributes": attrs})


# --------------------------------------------------------------------------- #
# ha_render_template
# --------------------------------------------------------------------------- #
_TPL_DESC = (
    "Rendert ein Home-Assistant-Jinja-Template serverseitig und gibt das Ergebnis "
    "als Text zurück. Mächtig zum Auslesen/Rechnen, z.B. "
    "\"{{ states('sensor.wohnzimmer_temperatur') }}\" oder "
    "\"{{ states.light | selectattr('state','eq','on') | list | count }}\"."
)

_TPL_SCHEMA = {
    "type": "object",
    "properties": {
        "template": {
            "type": "string",
            "description": "HA-Jinja-Template, z.B. \"{{ states('sensor.temp') }}\".",
        },
    },
    "required": ["template"],
}

_MAX_TPL = 2000


async def _render(args: dict, ctx: ToolContext) -> ToolResult:
    template = (args.get("template") or "").strip()
    if not template:
        return ToolResult.fail("Kein Template angegeben.")
    if len(template) > _MAX_TPL:
        return ToolResult.fail(f"Template zu lang (max {_MAX_TPL} Zeichen).")

    try:
        result = await client.render_template(template)
    except client.HAConfigError as exc:
        return ToolResult.fail(str(exc))
    except client.HAError as exc:
        return ToolResult.fail(str(exc))

    return ToolResult.ok({"result": result})


LIST_TOOL = Tool(
    name="ha_list_entities",
    description=_LIST_DESC,
    schema=_LIST_SCHEMA,
    execute=_list_entities,
    category="data",
)

STATE_TOOL = Tool(
    name="ha_get_state",
    description=_STATE_DESC,
    schema=_STATE_SCHEMA,
    execute=_get_state,
    category="data",
)

TEMPLATE_TOOL = Tool(
    name="ha_render_template",
    description=_TPL_DESC,
    schema=_TPL_SCHEMA,
    execute=_render,
    category="data",
)
