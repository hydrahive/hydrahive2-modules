"""Home-Assistant-Schreib-Tool — ha_call_service.

Ruft einen HA-Service auf (Licht schalten, Thermostat setzen, Szene aktivieren …).
Das ist die einzige zustandsändernde Operation des Moduls. Domain + Service werden
validiert; entity_id (falls als Ziel angegeben) ebenso. Alles geht durch den
client (URL+Token aus Settings).
"""
from __future__ import annotations

from hydrahive.tools.base import Tool, ToolContext, ToolResult

from . import client, validators

_DESCRIPTION = (
    "Ruft einen Home-Assistant-Service auf, um etwas zu schalten oder zu steuern. "
    "Beispiele: Licht an → domain='light', service='turn_on', entity_id='light.wohnzimmer'. "
    "Licht aus → service='turn_off'. Thermostat → domain='climate', "
    "service='set_temperature', entity_id='climate.bad', data={'temperature': 21}. "
    "Szene → domain='scene', service='turn_on', entity_id='scene.abend'. "
    "Für 'data' nur Service-spezifische Felder angeben (z.B. brightness_pct, color_name)."
)

_SCHEMA = {
    "type": "object",
    "properties": {
        "domain": {
            "type": "string",
            "description": "HA-Domain des Service, z.B. 'light', 'switch', 'climate', 'scene', 'cover'.",
        },
        "service": {
            "type": "string",
            "description": "Service-Name, z.B. 'turn_on', 'turn_off', 'toggle', 'set_temperature'.",
        },
        "entity_id": {
            "type": "string",
            "description": "Optional: Ziel-Entity, z.B. 'light.wohnzimmer'. Weglassen für service-weite Calls.",
        },
        "data": {
            "type": "object",
            "description": "Optional: zusätzliche Service-Daten, z.B. {'brightness_pct': 60} oder {'temperature': 21}.",
        },
    },
    "required": ["domain", "service"],
}


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    domain = (args.get("domain") or "").strip().lower()
    service = (args.get("service") or "").strip().lower()
    if not validators.is_domain(domain):
        return ToolResult.fail("Ungültige Domain (nur Kleinbuchstaben/Ziffern/_, z.B. 'light').")
    if not validators.is_service(service):
        return ToolResult.fail("Ungültiger Service (nur Kleinbuchstaben/Ziffern/_, z.B. 'turn_on').")

    payload: dict = {}
    raw_data = args.get("data")
    if isinstance(raw_data, dict):
        payload.update(raw_data)

    entity_id = (args.get("entity_id") or "").strip().lower()
    if entity_id:
        if not validators.is_entity(entity_id):
            return ToolResult.fail("Ungültige entity_id (Format: domain.objekt, z.B. light.wohnzimmer).")
        if validators.domain_of(entity_id) != domain:
            return ToolResult.fail(
                f"entity_id '{entity_id}' passt nicht zur Domain '{domain}'."
            )
        payload["entity_id"] = entity_id

    try:
        changed = await client.call_service(domain, service, payload)
    except client.HAConfigError as exc:
        return ToolResult.fail(str(exc))
    except client.HAError as exc:
        return ToolResult.fail(str(exc))

    if not changed:
        return ToolResult.ok({
            "message": f"{domain}.{service} ausgeführt (keine State-Änderung zurückgemeldet).",
            "changed": 0,
        })
    lines = [f"{c.get('name')} [{c.get('entity_id')}] → {c.get('state')}" for c in changed]
    return ToolResult.ok({
        "message": f"{domain}.{service} ausgeführt.",
        "changed": len(changed),
        "data": "\n".join(lines),
    })


TOOL = Tool(
    name="ha_call_service",
    description=_DESCRIPTION,
    schema=_SCHEMA,
    execute=_execute,
    category="action",
    prompt_hint=(
        "Schaltet/steuert echte Geräte im Zuhause. Bei mehrdeutigen Zielen erst "
        "ha_list_entities nutzen, um die genaue entity_id zu finden."
    ),
)
