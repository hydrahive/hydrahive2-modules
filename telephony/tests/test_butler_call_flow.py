"""„Anruf kommt rein“ im echten Anrufablauf (PLAN-BUTLER B1): Test-Anrufer (SIP) → Butler-Executor mit echtem
Ablauf → Entscheidung bestimmt, was passiert. Nur Platzhalter-Nummern.
"""
from __future__ import annotations

import json

import pytest
from _fake_caller import FakeCaller
from test_call import Hydra, _wait


@pytest.fixture
def butler(monkeypatch):
    """Echter Butler: Bausteine registriert, Abläufe im Test-Ordner, Inhaber = Benutzer „owner“."""
    import hydrahive.butler.registry as reg
    from backend import butler_events, butler_specs
    from hydrahive.butler import persistence as bp
    from hydrahive.butler.models import Flow

    reg.load_builtins()
    snap = (dict(reg.TRIGGERS), dict(reg.CONDITIONS), dict(reg.ACTIONS))
    for s in butler_specs.TRIGGERS:
        reg.register_trigger(s)
    for s in butler_specs.CONDITIONS:
        reg.register_condition(s)
    for s in butler_specs.ACTIONS:
        reg.register_action(s)
    monkeypatch.setattr(butler_events, "_owner_username", lambda cid: "owner" if cid == "cid1" else None)
    saved: list[str] = []

    def add(flow_id: str, nodes: list[dict], edges: list[dict], enabled: bool = True) -> None:
        bp.save_flow(Flow(flow_id=flow_id, name=flow_id, owner="owner", enabled=enabled, nodes=nodes, edges=edges),
                     modified_by="owner")
        saved.append(flow_id)
    yield add
    for f in saved:
        bp.delete_flow("owner", f)
    reg.TRIGGERS.clear(); reg.TRIGGERS.update(snap[0])
    reg.CONDITIONS.clear(); reg.CONDITIONS.update(snap[1])
    reg.ACTIONS.clear(); reg.ACTIONS.update(snap[2])


def _n(i, t, s, p=None):
    return {"id": i, "type": t, "subtype": s, "position": {"x": 0, "y": 0}, "params": p or {}}


def _e(i, a, b, h="output"):
    return {"id": i, "source": a, "target": b, "source_handle": h}


def _hydra(answer=None, assistant=None) -> Hydra:
    from backend.sip import dispatch

    h = Hydra(answer=answer)
    h.d.connection_id = "cid1"
    h.d.decide = lambda number: dispatch.butler_decide("cid1", number)
    if assistant is not None:
        h.d.assistant = assistant
    return h


def _call(h: Hydra, number: str = "0301234567") -> FakeCaller:
    c = FakeCaller()
    c.invite_from = number
    c.invite(h.addr)
    return c


def test_ablehnen_trotz_schalter_an(butler) -> None:
    butler("ablehnen", [_n("t", "trigger", "telephony_call_incoming", {"numbers": ["030 1234567"]}),
                        _n("a", "action", "telephony_reject")], [_e("e", "t", "a")])
    h = _hydra(answer="Hallo")
    c = _call(h)
    try:
        assert _wait(lambda: 480 in c.statuses())
        import time
        time.sleep(0.6)                                 # wäre danach doch abgenommen worden, käme jetzt 200
        assert h.records[0]["result"] == "rejected" and 200 not in c.statuses() and h.texts == []
    finally:
        c.close(); h.close()


def test_besetzt(butler) -> None:
    butler("besetzt", [_n("t", "trigger", "telephony_call_incoming"), _n("a", "action", "telephony_busy")],
           [_e("e", "t", "a")])
    h = _hydra(answer="Hallo")
    c = _call(h)
    try:
        assert _wait(lambda: 486 in c.statuses())
        assert h.records[0]["result"] == "busy"
    finally:
        c.close(); h.close()


def test_ablauf_gewinnt_bei_schalter_aus_ansage_mit_eigenem_text(butler) -> None:
    """Till 25.10.: Schalter aus + Ablauf sagt „annehmen“ → Ablauf gewinnt."""
    butler("ansage", [_n("t", "trigger", "telephony_call_incoming"),
                      _n("a", "action", "telephony_answer_greeting", {"text": "Bin im Urlaub."})], [_e("e", "t", "a")])
    h = _hydra(answer=None)
    c = _call(h)
    try:
        assert _wait(lambda: 200 in c.statuses())
        assert _wait(lambda: h.records, timeout=5)
        assert h.texts == ["Bin im Urlaub."] and h.records[0]["kind"] == "greeting"
    finally:
        c.close(); h.close()


def test_bedingung_nummer_nein_zweig_wie_einstellungen(butler) -> None:
    butler("familie", [_n("t", "trigger", "telephony_call_incoming"),
                       _n("c", "condition", "telephony_caller", {"mode": "starts_with", "value": "0151"}),
                       _n("a", "action", "telephony_answer_greeting", {"text": "Familie"}),
                       _n("d", "action", "telephony_default")],
           [_e("e1", "t", "c"), _e("e2", "c", "a", "true"), _e("e3", "c", "d", "false")])
    h = _hydra(answer=None)
    c = _call(h, "0301234567")
    try:
        assert _wait(lambda: 480 in c.statuses()), "nicht 0151 → Einstellungen (Schalter aus) → abgelehnt"
    finally:
        c.close(); h.close()


def test_kein_passender_ablauf_wie_bisher(butler) -> None:
    butler("andere", [_n("t", "trigger", "telephony_call_incoming", {"numbers": ["0151 2345678"]}),
                      _n("a", "action", "telephony_reject")], [_e("e", "t", "a")])
    h = _hydra(answer="Hallo")
    c = _call(h, "0301234567")
    try:
        assert _wait(lambda: 200 in c.statuses()), "Schalter an → Ansage wie bisher"
        assert _wait(lambda: h.records, timeout=5) and h.texts == ["Hallo"]
    finally:
        c.close(); h.close()


def test_ausgeschalteter_ablauf_zaehlt_nicht(butler) -> None:
    butler("aus", [_n("t", "trigger", "telephony_call_incoming"), _n("a", "action", "telephony_reject")],
           [_e("e", "t", "a")], enabled=False)
    h = _hydra(answer="Hallo")
    c = _call(h)
    try:
        assert _wait(lambda: 200 in c.statuses())
    finally:
        c.close(); h.close()


def test_assistent_mit_eigenem_wissen_und_name(butler) -> None:
    from backend.agent.prompt import AgentConfig

    butler("assi", [_n("t", "trigger", "telephony_call_incoming"),
                    _n("a", "action", "telephony_answer_assistant", {"knowledge": "Ich bin heute im Büro Beispiel.",
                                                                     "name": "Max Mustermann"})], [_e("e", "t", "a")])
    seen: list = []

    def llm(messages):
        seen.append(messages[0]["content"])
        return json.dumps({"say": "Tschüss.", "end": True})

    def settings():                                    # wie assistant.bundle_any: Einstellungen, egal welcher Modus
        return {"cfg": AgentConfig("Beispiel GmbH", "Öffnungszeiten: Mo–Fr."), "llm": llm, "stt": lambda p: "Hallo",
                "tts": lambda t, c: b"\x22" * 800, "options": {"no_input_ms": 800, "end_silence_ms": 300}}
    from test_call_assistant import _media_port, _send_voice, _tone_pcma

    h = _hydra(answer=None, assistant=lambda: None)          # Modus „Nur Ansage“, Schalter aus
    h.d.assistant_settings = settings
    c = FakeCaller(send_rtp=False)
    c.invite(h.addr)
    try:
        assert _wait(lambda: 200 in c.statuses())
        _send_voice(c, _media_port(c), _tone_pcma(500) + bytes([0xD5]) * 8 * 500)
        assert _wait(lambda: h.records, timeout=8)
        assert h.records[0]["kind"] == "assistant", "Ablauf erzwingt den Assistenten, auch im Modus „Nur Ansage“"
    finally:
        c.close(); h.close()
    assert seen, "das Modell wurde gefragt"
    assert "Ich bin heute im Büro Beispiel." in seen[0] and "Max Mustermann" in seen[0]
    assert "Öffnungszeiten" not in seen[0], "eigenes Wissen ersetzt das aus den Einstellungen"


def test_butler_fehler_oder_zu_langsam_wie_bisher(monkeypatch) -> None:
    from backend import butler_events
    from backend.sip import dispatch

    def boom(event):
        raise RuntimeError("kaputt")
    monkeypatch.setattr(butler_events, "_owner_username", lambda cid: "owner")
    monkeypatch.setattr(butler_events, "_dispatch", boom)
    assert dispatch.butler_decide("cid1", "0301234567") is None

    async def slow(event):
        import asyncio
        await asyncio.sleep(5)
    monkeypatch.setattr(butler_events, "_dispatch", slow)
    import time
    t = time.monotonic()
    assert butler_events.decide("cid1", "0301234567", timeout=0.3) is None and time.monotonic() - t < 2


def test_nummer_kommt_aus_dem_from_kopf(butler) -> None:
    from backend.sip import dispatch

    got: list = []
    h = Hydra(answer="Hallo")
    h.d.decide = lambda number: got.append(number)
    c = _call(h, "+49301234567")
    try:
        assert _wait(lambda: got)
        assert got == ["+49301234567"], "roh weitergeben – aufbereitet wird in butler_events.normalize"
    finally:
        c.close(); h.close()
    assert dispatch.butler_decide("unbekannt", "0301234567") is None, "Verbindung ohne Inhaber → keine Entscheidung"
