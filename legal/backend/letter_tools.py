"""Brief-Werkzeuge des Rechts-Agenten (Plan L3 Schritt 5). Rechte wie die übrigen Fall-Werkzeuge (case_tools.scope).

- legal_letter_draft: Gerüst aus Vorlage + Fallakte (liest nur).
- legal_check_letter: Prüfliste für einen Entwurf (speichert nichts).
- legal_propose_letter: Brief als Vorschlag ablegen; erst „Übernehmen“ legt ihn als Entwurf in den Schriftverkehr.
"""
from __future__ import annotations

from typing import Any

from hydrahive.tools.base import Tool, ToolContext, ToolResult

from . import casefile, letter_check, letter_templates
from .case_tools import _agent_name, _fail, scope
from .cases import CaseError, get_case
from .letter_check import DELIVERY

_S: dict[str, Any] = {"type": "string"}
_LETTER_PROPS = {
    "letter_type": {"type": "string", "enum": list(letter_templates.ORDER) + ["sonstiges"]},
    "sender": {"type": "string", "description": "Name + Anschrift, je Zeile (Beteiligter „Ich / wir“)."},
    "recipient": {"type": "string", "description": "Name + Anschrift, je Zeile."},
    "date": {"type": "string", "description": "Briefdatum JJJJ-MM-TT."},
    "their_ref": _S, "our_ref": _S,
    "subject": _S,
    "body": {"type": "string", "description": "Brieftext mit Anrede und Gruß. Fristen immer als Datum (TT.MM.JJJJ)."},
    "delivery": {"type": "string", "enum": list(DELIVERY)},
    "attachments": {"type": "array", "items": _S, "maxItems": 30},
}


async def _draft(args: dict, ctx: ToolContext) -> ToolResult:
    pid, err = scope(ctx, "read")
    if err:
        return err
    rid = args.get("recipient_id")
    try:
        out = letter_templates.draft(str(args.get("template") or ""), case=get_case(pid) or {},
                                     parties=casefile.list_parties(pid), recipient_id=int(rid) if rid else None)
    except letter_templates.TemplateError as e:
        return ToolResult.fail(f"Abgelehnt: {e.code} (Vorlagen: {', '.join(letter_templates.ORDER)})")
    except (TypeError, ValueError):
        return ToolResult.fail("recipient_id muss die ID eines Beteiligten dieses Falls sein.")
    return ToolResult.ok({**out, "hint": "Gerüst – [Platzhalter] mit Fakten aus der Akte füllen, Normen mit legal_norm "
                                         "prüfen, dann legal_check_letter und legal_propose_letter."})


async def _check(args: dict, ctx: ToolContext) -> ToolResult:
    pid, err = scope(ctx, "read")
    if err:
        return err
    return ToolResult.ok(letter_check.check(dict(args), case=get_case(pid)))


async def _propose(args: dict, ctx: ToolContext) -> ToolResult:
    pid, err = scope(ctx, "write")
    if err:
        return err
    try:
        out = casefile.propose(pid, "letter", dict(args), author_name=_agent_name(ctx))
    except CaseError as e:
        return _fail(e)
    return ToolResult.ok({**out, "hint": "Brief als Vorschlag abgelegt. Der Mensch prüft ihn (Prüfliste), übernimmt ihn "
                                         "als Entwurf in den Schriftverkehr und verschickt selbst. Nichts wurde versendet."})


LETTER_DRAFT = Tool(
    name="legal_letter_draft", category="legal", execute=_draft,
    description="Brief-Gerüst aus einer Vorlage und der Fallakte (Absender = Beteiligter „Ich / wir“, Empfänger = "
                "recipient_id, Aktenzeichen, Datum). Vorlagen: " + ", ".join(letter_templates.ORDER) + ". Speichert nichts.",
    schema={"type": "object", "properties": {"template": {"type": "string", "enum": list(letter_templates.ORDER)},
                                             "recipient_id": {"type": "integer"}}, "required": ["template"]})
CHECK_LETTER = Tool(
    name="legal_check_letter", category="legal", execute=_check,
    description="Prüfliste für einen Brief-Entwurf: Absender/Empfänger mit Anschrift, Datum, Betreff, Aktenzeichen, Frist "
                "als Datum, Normen im Korpus belegt, Zustellweg, Anlagen. Speichert nichts. Vor legal_propose_letter nutzen.",
    schema={"type": "object", "properties": _LETTER_PROPS, "required": ["body"]})
PROPOSE_LETTER = Tool(
    name="legal_propose_letter", category="legal", execute=_propose,
    description="Legt einen Brief als VORSCHLAG in der Fallakte ab (mit Prüfliste). Versendet nichts; der Mensch übernimmt "
                "ihn als Entwurf und verschickt selbst.",
    schema={"type": "object", "properties": _LETTER_PROPS,
            "required": ["letter_type", "sender", "recipient", "date", "subject", "body", "delivery"]})

TOOLS = [LETTER_DRAFT, CHECK_LETTER, PROPOSE_LETTER]
