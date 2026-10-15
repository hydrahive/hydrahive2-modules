"""Butler-Aktion „Auf Vitrine anzeigen“: Flows blenden Ereignisse auf dem Gehäuse-Display ein."""
from __future__ import annotations

from hydrahive.butler.models import TriggerEvent
from hydrahive.butler.registry import ActionResult, ActionSpec, ParamSchema
from hydrahive.butler.template import render
from renderer import inbox

from . import notify


async def _execute(params: dict, event: TriggerEvent) -> ActionResult:
    text = notify.safe_text(render(str(params.get("text") or ""), event), event.owner)
    title = notify.safe_text(render(str(params.get("title") or ""), event), event.owner)
    try:
        seconds = int(params["seconds"]) if str(params.get("seconds") or "").strip() else None
        m = inbox.post(notify.data_dir(), text, kind=str(params.get("kind") or "info"), title=title,
                       seconds=seconds, source="butler")
    except (inbox.InboxError, ValueError) as e:
        return ActionResult(ok=False, detail=f"Vitrine: {e}")
    return ActionResult(ok=True, detail=f"Vitrine: eingeblendet ({m['kind']})")


ACTION = ActionSpec(
    subtype="vitrine_message",
    label="Auf Vitrine anzeigen",
    description="Blendet eine Karte auf dem Gehäuse-Display ein. Text/Titel dürfen {{event.…}}-Platzhalter enthalten.",
    params=[
        ParamSchema(key="text", label="Text", kind="textarea", required=True, placeholder="{{event.contact_label}}: {{event.message_text}}"),
        ParamSchema(key="title", label="Überschrift (optional)", kind="text"),
        ParamSchema(key="kind", label="Stil", kind="select", options=list(inbox.KINDS), default="info"),
        ParamSchema(key="seconds", label="Sekunden (3–600, leer = Standard)", kind="number"),
    ],
    execute=_execute,
)
