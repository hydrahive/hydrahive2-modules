"""Fall-Werkzeuge des Rechts-Agenten (Plan L2 Schritt 5). Muster: storyteller/backend/agent_tools.scope().

Alle Fall-Werkzeuge arbeiten nur auf ``ToolContext.project_id`` und prüfen die Projektrolle des Nutzers, für den der
Agent läuft. Schreibende Werkzeuge legen nur Vorschläge bzw. Notizen ab. ``legal_deadline`` rechnet und speichert
nichts; ohne Fall braucht es ein Bundesland. Fall-Werkzeuge stehen im Manifest unter ``sensitive_tools`` als privat.
"""
from __future__ import annotations

from typing import Any

from hydrahive.tools.base import Tool, ToolContext, ToolResult

from . import casefile
from .access import case_access
from .cases import CaseError, get_case
from .holidays_de import STATES


def scope(ctx: ToolContext, need: str = "read") -> tuple[str | None, ToolResult | None]:
    pid = (ctx.project_id or "").strip()
    if not pid:
        return None, ToolResult.fail("Dieser Chat gehört zu keinem Fall. Den Chat aus dem Fall starten "
                                     "(Recht → Fälle → „Mit dem Rechts-Agenten sprechen“).")
    from hydrahive.api.middleware.users import get_by_username
    user = get_by_username(ctx.user_id or "") or {}
    result = case_access(ctx.user_id or "", user.get("role", "user"), pid, need)
    if result == "missing":
        return None, ToolResult.fail("Kein Zugriff: Dieses Projekt ist kein Fall oder du bist nicht Mitglied.")
    if result == "read_only":
        return None, ToolResult.fail("Nur Leserechte in diesem Fall – Vorschläge und Notizen sind nicht erlaubt.")
    return pid, None


def _agent_name(ctx: ToolContext) -> str:
    from hydrahive.agents import config as agent_config
    agent = agent_config.get(ctx.agent_id or "") or {}
    return str(agent.get("name") or "Rechts-Agent")[:200]


def _fail(e: CaseError) -> ToolResult:
    detail = ", ".join(f"{k}={v}" for k, v in e.params.items())
    return ToolResult.fail(f"Abgelehnt: {e.code}" + (f" ({detail})" if detail else ""))


async def _case(args: dict, ctx: ToolContext) -> ToolResult:
    pid, err = scope(ctx, "read")
    if err:
        return err
    return ToolResult.ok(casefile.snapshot(pid))


async def _deadline(args: dict, ctx: ToolContext) -> ToolResult:
    state = str(args.get("state") or "").strip().upper()
    if not state and ctx.project_id:
        pid, err = scope(ctx, "read")
        if err:
            return err
        state = (get_case(pid) or {}).get("state", "")
    if not state:
        return ToolResult.fail("Bundesland fehlt (state, z. B. NW) – ohne Fall gibt es keinen Standard.")
    try:
        result = casefile.calc(args, state)
    except CaseError as e:
        return _fail(e)
    return ToolResult.ok(result)


def _proposer(kind: str):
    async def run(args: dict, ctx: ToolContext) -> ToolResult:
        pid, err = scope(ctx, "write")
        if err:
            return err
        try:
            out = casefile.propose(pid, kind, dict(args), author_name=_agent_name(ctx))
        except CaseError as e:
            return _fail(e)
        return ToolResult.ok({**out, "hint": "Vorschlag abgelegt – der Mensch übernimmt oder verwirft ihn in der "
                                             "Fallakte (Reiter Vorschläge). Die Akte ist unverändert."})
    return run


async def _note(args: dict, ctx: ToolContext) -> ToolResult:
    pid, err = scope(ctx, "write")
    if err:
        return err
    try:
        out = casefile.add_note(pid, author="agent", author_name=_agent_name(ctx), title=args.get("title", ""),
                                body=args.get("body", ""), citations=list(args.get("citations") or []))
    except CaseError as e:
        return _fail(e)
    missing = [c["citation"] for c in out["citations"] if not c["found"]]
    if missing:
        out["warning"] = f"Nicht im Korpus gefunden: {', '.join(missing)} – prüfen, bevor du dich darauf stützt."
    return ToolResult.ok(out)


_S: dict[str, Any] = {"type": "string"}
_DEADLINE_PROPS = {
    "event_date": {"type": "string", "description": "Ereignistag JJJJ-MM-TT (z. B. Zugang des Schreibens)."},
    "kind": {"type": "string", "enum": ["days", "weeks", "months", "years", "date"]},
    "amount": {"type": "integer", "minimum": 0, "description": "Anzahl; bei kind=date 0."},
    "start_rule": {"type": "string", "enum": ["event", "day_start"],
                   "description": "event = § 187 Abs. 1 (Standard), day_start = § 187 Abs. 2."},
}

LEGAL_CASE = Tool(
    name="legal_case", category="legal", execute=_case,
    description="Liest die Fallakte dieses Falls: Sachverhalt, Ziel, Bundesland, Beteiligte, Fristen (mit Rechenweg), "
                "Notizen und Anzahl offener Vorschläge. Zuerst aufrufen.",
    schema={"type": "object", "properties": {}})
DEADLINE = Tool(
    name="legal_deadline", category="legal", execute=_deadline,
    description="Rechnet eine Frist nach §§ 187, 188, 193 BGB mit Rechenweg und Feiertagen des Bundeslands (Standard: "
                "Land des Falls). Speichert nichts – zum Festhalten legal_propose_deadline. Sonderregeln (ZPO, "
                "Zustellung) beachtet es nicht; immer den Rechenweg und die Hinweise mit ausgeben.",
    schema={"type": "object", "properties": {**_DEADLINE_PROPS, "state": {
        "type": "string", "enum": list(STATES), "description": "Bundesland-Kürzel; ohne Fall Pflicht."}},
        "required": ["event_date", "kind", "amount"]})
PROPOSE_PARTY = Tool(
    name="legal_propose_party", category="legal", execute=_proposer("party"),
    description="Schlägt einen Beteiligten für die Fallakte vor (Gegenseite, Anwalt, Behörde …). Ändert nichts direkt.",
    schema={"type": "object", "properties": {
        "role": {"type": "string", "enum": list(casefile.PARTY_ROLES)}, "name": _S, "address": _S, "contact": _S,
        "note": _S}, "required": ["role", "name"]})
PROPOSE_DEADLINE = Tool(
    name="legal_propose_deadline", category="legal", execute=_proposer("deadline"),
    description="Schlägt eine Frist für die Fallakte vor; sie wird mit dem Land des Falls gerechnet und mit Rechenweg "
                "angezeigt. Ändert nichts direkt.",
    schema={"type": "object", "properties": {"label": {"type": "string", "description": "Wofür, z. B. „Widerspruch "
                                                       "gegen Bescheid vom 01.10.“"}, **_DEADLINE_PROPS, "note": _S},
            "required": ["label", "event_date", "kind", "amount"]})
PROPOSE_FACT = Tool(
    name="legal_propose_fact", category="legal", execute=_proposer("fact"),
    description="Schlägt eine Tatsache zur Ergänzung des Sachverhalts vor (mit Datum und Beleg, wenn bekannt). Ändert "
                "nichts direkt.",
    schema={"type": "object", "properties": {"text": _S}, "required": ["text"]})
NOTE = Tool(
    name="legal_note", category="legal", execute=_note,
    description="Hält ein Recherche-Ergebnis in der Fallakte fest. Normen in citations angeben (z. B. „§ 536c BGB“); "
                "sie werden gegen den Korpus geprüft.",
    schema={"type": "object", "properties": {"title": _S, "body": _S,
                                             "citations": {"type": "array", "items": _S, "maxItems": 20}},
            "required": ["title", "body"]})

TOOLS = [LEGAL_CASE, DEADLINE, PROPOSE_PARTY, PROPOSE_DEADLINE, PROPOSE_FACT, NOTE]
