"""Butler – „Anruf kommt rein“ (PLAN-BUTLER Etappe B1): Bausteine und Entscheidung mit dem echten Butler-Executor.

Nur Platzhalter-Nummern. Die Abläufe liegen in einem Test-Ordner (Butler-Persistenz über settings im Test-Kern).
"""
from __future__ import annotations

import asyncio

import pytest


@pytest.fixture
def specs():
    import hydrahive.butler.registry as reg
    from backend import butler_specs

    reg.load_builtins()
    snap = (dict(reg.TRIGGERS), dict(reg.CONDITIONS), dict(reg.ACTIONS))
    for s in butler_specs.TRIGGERS:
        reg.register_trigger(s)
    for s in butler_specs.CONDITIONS:
        reg.register_condition(s)
    for s in butler_specs.ACTIONS:
        reg.register_action(s)
    yield butler_specs
    reg.TRIGGERS.clear(); reg.TRIGGERS.update(snap[0])
    reg.CONDITIONS.clear(); reg.CONDITIONS.update(snap[1])
    reg.ACTIONS.clear(); reg.ACTIONS.update(snap[2])


def _event(number: str = "0301234567", owner: str = "owner"):
    from backend import butler_events

    return butler_events.incoming_event(owner, "cid1", number)


def test_ereignis_nummer_normalisiert_als_kontakt() -> None:
    from backend import butler_events

    e = butler_events.incoming_event("owner", "cid1", "+49301234567")
    assert e.event_type == "telephony_call_incoming" and e.owner == "owner" and e.channel == "telephone"
    assert e.contact_id == "0301234567" and e.payload["number"] == "0301234567"
    assert e.payload["number_masked"] == "•••567" and e.payload["anonymous"] is False
    anon = butler_events.incoming_event("owner", "cid1", "")
    assert anon.contact_id is None and anon.payload["anonymous"] is True and anon.payload["number"] == ""


def test_nummer_aus_from_kopf() -> None:
    from backend import butler_events

    assert butler_events.caller_number('"Max" <sip:+49301234567@fritz.box>;tag=x') == "0301234567"
    assert butler_events.caller_number("<sip:0301234567@fritz.box>") == "0301234567"
    assert butler_events.caller_number("<sip:anonymous@anonymous.invalid>") == ""
    assert butler_events.caller_number("<sip:**610@fritz.box>") == ""


def test_ausloeser_nur_bei_anruf_und_optional_nur_bestimmte_nummern(specs) -> None:
    t = specs.TRIGGER_INCOMING
    assert t.matches({}, _event()) is True
    assert t.matches({"numbers": ["030 1234567"]}, _event()) is True
    assert t.matches({"numbers": ["+49 30 1234567"]}, _event()) is True, "Schreibweise egal"
    assert t.matches({"numbers": ["0151 2345678"]}, _event()) is False
    assert t.matches({"numbers": ["0151 2345678"]}, _event("")) is False
    from hydrahive.butler.models import TriggerEvent
    assert t.matches({}, TriggerEvent(event_type="message")) is False


@pytest.mark.parametrize("params, number, expect", [
    ({"mode": "starts_with", "value": "030"}, "0301234567", True),
    ({"mode": "starts_with", "value": "+4930"}, "0301234567", True),
    ({"mode": "starts_with", "value": "0151"}, "0301234567", False),
    ({"mode": "one_of", "value": "0151 2345678\n030 1234567"}, "0301234567", True),
    ({"mode": "one_of", "value": "0151 2345678"}, "0301234567", False),
    ({"mode": "anonymous"}, "", True),
    ({"mode": "anonymous"}, "0301234567", False),
    ({"mode": "starts_with", "value": ""}, "0301234567", False),
    ({"mode": "kaputt", "value": "030"}, "0301234567", False),
])
def test_bedingung_anrufer_nummer(specs, params, number, expect) -> None:
    assert specs.CONDITION_CALLER.evaluate(params, _event(number)) is expect


def _run(coro):
    return asyncio.run(coro)


def test_aktionen_liefern_entscheidung(specs) -> None:
    from backend import butler_events

    ev = _event()
    cases = [
        ("telephony_answer_assistant", {"knowledge": "Ich bin im Urlaub.", "name": "Max Mustermann"},
         {"action": "assistant", "knowledge": "Ich bin im Urlaub.", "name": "Max Mustermann"}),
        ("telephony_answer_assistant", {}, {"action": "assistant"}),
        ("telephony_answer_greeting", {"text": "Bin gleich zurück."}, {"action": "greeting", "text": "Bin gleich zurück."}),
        ("telephony_reject", {}, {"action": "reject"}),
        ("telephony_busy", {}, {"action": "busy"}),
        ("telephony_default", {}, {"action": "default"}),
    ]
    for subtype, params, want in cases:
        spec = next(a for a in specs.ACTIONS if a.subtype == subtype)
        res = _run(spec.execute(params, ev))
        assert res.ok and butler_events.decision_of(res) == want, subtype


def test_aktion_auf_falschem_ereignis_entscheidet_nichts(specs) -> None:
    from backend import butler_events
    from hydrahive.butler.models import TriggerEvent

    spec = next(a for a in specs.ACTIONS if a.subtype == "telephony_reject")
    res = _run(spec.execute({}, TriggerEvent(event_type="message")))
    assert res.ok is False and butler_events.decision_of(res) is None


def test_ueberschreibungen_begrenzt_und_ohne_steuerzeichen(specs) -> None:
    from backend import butler_events

    spec = next(a for a in specs.ACTIONS if a.subtype == "telephony_answer_assistant")
    d = butler_events.decision_of(_run(spec.execute({"knowledge": "x" * 9000 + "\x00", "name": "y" * 500}, _event())))
    assert len(d["knowledge"]) == 4000 and "\x00" not in d["knowledge"] and len(d["name"]) == 80
    g = next(a for a in specs.ACTIONS if a.subtype == "telephony_answer_greeting")
    assert len(butler_events.decision_of(_run(g.execute({"text": "z" * 900}, _event())))["text"]) == 500


def test_verbindung_haengt_butler_an_den_verteiler(monkeypatch) -> None:
    """connections._config → SipAgent → CallDispatcher bekommt decide/has_flows/greeting_text/assistant_settings."""
    from backend import connections
    from backend.sip.agent import SipAgent

    hooks = connections.butler_hooks("cid1")
    assert set(hooks) == {"decide", "has_flows", "greeting_text", "assistant_settings"}
    a = SipAgent(connection_id="cid1", user="u", password="p", domain="fritz.box", target=("127.0.0.1", 9),
                 bind=("127.0.0.1", 0), display_name="H", interval=300, call_butler=hooks)
    assert a.calls.decide is hooks["decide"] and a.calls.has_flows is hooks["has_flows"]
    assert a.calls.assistant_settings is hooks["assistant_settings"]


def test_ohne_ablauf_wird_der_butler_nicht_gefragt() -> None:
    """Gibt es keinen Ablauf mit „Anruf kommt rein“, läuft der Anruf genau wie vor B1 (Policy sofort)."""
    from test_call import Hydra

    asked: list = []
    h = Hydra(answer=None)
    h.d.decide = lambda n: asked.append(n)
    h.d.has_flows = lambda: False
    from _fake_caller import FakeCaller
    from test_call import _wait
    c = FakeCaller()
    try:
        c.invite(h.addr)
        assert _wait(lambda: 480 in c.statuses())
        assert asked == [] and 180 not in c.statuses(), "sofort 480 wie bisher, ohne Klingeln"
    finally:
        c.close(); h.close()


def test_modul_registriert_die_bausteine() -> None:
    import backend
    from hydrahive.modules.context import ModuleContext

    ctx = ModuleContext("telephony")
    ctx.register_router = lambda r: None
    ctx.register_migrations = lambda d: None
    ctx.register_job = lambda *a, **k: None
    backend.register(ctx)
    assert [s.subtype for s in ctx.butler_triggers] == ["telephony_call_incoming"]
    assert [s.subtype for s in ctx.butler_conditions] == ["telephony_caller"]
    assert {s.subtype for s in ctx.butler_actions} == {"telephony_answer_assistant", "telephony_answer_greeting",
                                                       "telephony_reject", "telephony_busy", "telephony_default"}


def test_unbekannte_oder_kaputte_entscheidung_wird_verworfen() -> None:
    from backend import butler_events
    from hydrahive.butler.registry import ActionResult

    for detail in ['telephony:{"action": "rm -rf"}', "telephony:[1]", "telephony:kaputt", "andere:{}", None]:
        assert butler_events.decision_of(ActionResult(ok=True, detail=detail)) is None, detail
    assert butler_events.decision_of({"detail": 'telephony:{"action": "busy"}'}) == {"action": "busy"}
