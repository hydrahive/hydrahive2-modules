"""Butler-Bausteine des VoIP-Moduls (PLAN-BUTLER Etappe B1): „Anruf kommt rein“.

Auslöser feuert beim Klingeln; Aktionen geben eine Entscheidung zurück (annehmen mit Assistent/Ansage, ablehnen,
besetzt, normal), die ``butler_events.decide`` ausliest. Wochentag/Uhrzeit/„Kontakt in Liste“ liefert der Kern.
Hinweis: Die angezeigte Nummer ist nicht geprüft (kann gefälscht sein) – nur zum Sortieren, nie als Berechtigung.
"""
from __future__ import annotations

from hydrahive.butler.models import TriggerEvent
from hydrahive.butler.registry import (
    ActionResult,
    ActionSpec,
    ConditionSpec,
    ParamSchema,
    TriggerSpec,
)

from .agent.prompt import MAX_KNOWLEDGE, _clean
from .butler_events import EVENT_INCOMING, decision_result, normalize

_UNCHECKED = " Die Nummer ist nicht geprüft und kann gefälscht sein – nur zum Sortieren."


def _numbers(raw) -> set[str]:
    items = raw if isinstance(raw, list) else str(raw or "").replace(",", "\n").split("\n")
    return {n for n in (normalize(str(x)) for x in items) if n}


def _match_incoming(params: dict, event: TriggerEvent) -> bool:
    if event.event_type != EVENT_INCOMING:
        return False
    want = _numbers(params.get("numbers"))
    return not want or (event.payload.get("number") or "") in want


TRIGGER_INCOMING = TriggerSpec(
    subtype="telephony_call_incoming", label="Anruf kommt rein",
    description="Feuert, während es klingelt – bevor HydraHive abnimmt. Der Ablauf entscheidet, was mit dem Anruf "
                "passiert; ohne Entscheidung gelten die VoIP-Einstellungen." + _UNCHECKED,
    params=[ParamSchema(key="numbers", label="Nur diese Nummern (optional)", kind="list_text",
                        placeholder="030 1234567")],
    matches=_match_incoming)


def _eval_caller(params: dict, event: TriggerEvent) -> bool:
    number = event.payload.get("number") or ""
    mode = params.get("mode")
    if mode == "anonymous":
        return not number
    if mode == "starts_with":
        prefix = normalize(str(params.get("value") or ""))
        return bool(prefix and number and number.startswith(prefix))
    if mode == "one_of":
        return bool(number) and number in _numbers(params.get("value"))
    return False


CONDITION_CALLER = ConditionSpec(
    subtype="telephony_caller", label="Anrufer-Nummer",
    description="Prüft die Nummer des Anrufers: beginnt mit (z. B. Vorwahl), ist eine von (eine je Zeile) oder ist "
                "unterdrückt." + _UNCHECKED,
    params=[ParamSchema(key="mode", label="Prüfung", kind="select", required=True,
                        options=["starts_with", "one_of", "anonymous"], default="starts_with"),
            ParamSchema(key="value", label="Nummer(n)", kind="textarea", placeholder="030")],
    evaluate=_eval_caller)


def _decide(build):
    async def execute(params: dict, event: TriggerEvent) -> ActionResult:
        if event.event_type != EVENT_INCOMING:
            return ActionResult(ok=False, detail="nur_bei_anruf_kommt_rein")
        return decision_result(build(params))
    return execute


def _assistant(params: dict) -> dict:
    d: dict = {"action": "assistant"}
    knowledge = _clean(str(params.get("knowledge") or ""), MAX_KNOWLEDGE).strip()
    name = _clean(str(params.get("name") or ""), 80).replace("\n", " ").strip()
    if knowledge:
        d["knowledge"] = knowledge
    if name:
        d["name"] = name
    return d


def _greeting(params: dict) -> dict:
    text = _clean(str(params.get("text") or ""), 500).strip()
    return {"action": "greeting", **({"text": text} if text else {})}


ACTIONS = [
    ActionSpec(subtype="telephony_answer_assistant", label="Mit Assistent annehmen",
               description="Der KI-Assistent nimmt ab. Optional eigenes Wissen und eigener Name nur für diesen "
                           "Ablauf (leer = VoIP-Einstellungen). Der Anrufer bleibt ein Fremder.",
               params=[ParamSchema(key="knowledge", label="Wissen (optional)", kind="textarea"),
                       ParamSchema(key="name", label="Name (optional)", kind="text", placeholder="Max Mustermann")],
               execute=_decide(_assistant)),
    ActionSpec(subtype="telephony_answer_greeting", label="Mit Ansage annehmen",
               description="HydraHive nimmt ab, liest die Ansage vor und legt auf (leer = Ansage aus den Einstellungen).",
               params=[ParamSchema(key="text", label="Ansage (optional)", kind="textarea")],
               execute=_decide(_greeting)),
    ActionSpec(subtype="telephony_reject", label="Anruf ablehnen",
               description="HydraHive nimmt nicht ab – andere Telefone derselben Rufnummer klingeln weiter.",
               params=[], execute=_decide(lambda p: {"action": "reject"})),
    ActionSpec(subtype="telephony_busy", label="Besetzt",
               description="Der Anrufer hört besetzt.", params=[], execute=_decide(lambda p: {"action": "busy"})),
    ActionSpec(subtype="telephony_default", label="Wie in den Einstellungen",
               description="Nichts entscheiden – es gilt, was in den VoIP-Einstellungen steht.",
               params=[], execute=_decide(lambda p: {"action": "default"})),
]
TRIGGERS = [TRIGGER_INCOMING]
CONDITIONS = [CONDITION_CALLER]
