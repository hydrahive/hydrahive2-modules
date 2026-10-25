"""Gesprächsschleife bei ausgehenden Anrufen (PLAN-ANRUFEN-3, 3b): Gegenseite meldet sich zuerst, dann Vorstellung,
dann nennt der Assistent von sich aus den Grund. Fake-Whisper/-Modell/-Piper wie in test_conversation.py.
"""
from __future__ import annotations

import json
import threading
import time

from test_conversation import Line, _silence, _speech


def _run(line: Line, replies, *, transcripts=None, **kw):
    from backend.agent import prompt_out
    from backend.agent.conversation import Conversation

    replies, transcripts = list(replies), list(transcripts or [])
    seen: list[list[dict]] = []

    def llm(messages):
        seen.append(messages)
        r = replies.pop(0) if replies else {"say": "Auf Wiederhören!", "end": True}
        return json.dumps(r, ensure_ascii=False)

    def stt(pcm16k: bytes) -> str:
        return transcripts.pop(0) if transcripts else "Hallo"

    cfg = prompt_out.OutboundConfig("Max Mustermann", "Frag nach einem Termin.", "")
    opts = {"no_input_ms": 1500, "max_seconds": 10, "end_silence_ms": 300, "thinking_after": 5.0,
            "messages": prompt_out.build_messages, "greet": prompt_out.greeting, "opening": True,
            "wait_first": 0.6}
    opts.update(kw)
    conv = Conversation(cfg=cfg, llm=llm, stt=stt, say=line.say, frames=line.inbox, hangup=line.hung_up.is_set, **opts)
    result: dict = {}
    t = threading.Thread(target=lambda: result.update(r=conv.run()), daemon=True)
    t.start()
    return t, result, seen


def test_gegenseite_meldet_sich_dann_vorstellung_dann_grund() -> None:
    line = Line()
    line.talk(_speech(400) + _silence(400))
    t, res, seen = _run(line, [{"say": "Ich rufe wegen eines Termins an. Wann hätten Sie Zeit?"},
                               {"say": "Danke, auf Wiederhören!", "notes": {"result": "Di 10 Uhr frei."}, "end": True}],
                        transcripts=["Autohaus Beispiel, guten Tag.", "Dienstag um zehn."])
    time.sleep(2.2)
    line.talk(_speech(400) + _silence(400))
    t.join(6)
    r = res["r"]
    assert "Max Mustermann" in line.said[0] and "KI" in line.said[0], "zuerst die Vorstellung"
    assert line.said[1] == "Ich rufe wegen eines Termins an. Wann hätten Sie Zeit?", "dann von sich aus der Grund"
    assert seen[0][0]["role"] == "system" and "DU hast angerufen" in seen[0][0]["content"]
    assert seen[0][1] == {"role": "user", "content": "<gegenseite>Autohaus Beispiel, guten Tag.</gegenseite>"}
    assert r.reason == "assistant_end" and r.turns == 2 and r.notes == {"result": "Di 10 Uhr frei."}


def test_gegenseite_sagt_nichts_assistent_beginnt_trotzdem() -> None:
    from backend.agent.conversation import OPENING_SILENT

    line = Line()
    t, res, seen = _run(line, [{"say": "Ich rufe wegen eines Termins an.", "end": True}])
    t.join(5)
    assert "KI" in line.said[0] and line.said[1] == "Ich rufe wegen eines Termins an."
    assert seen[0][1]["content"] == f"<gegenseite>{OPENING_SILENT}</gegenseite>"
    assert res["r"].reason == "assistant_end"


def test_auflegen_bevor_der_assistent_spricht() -> None:
    line = Line()
    t, res, seen = _run(line, [], wait_first=2.0)
    time.sleep(0.2)
    line.hung_up.set()
    t.join(3)
    assert res["r"].reason == "caller_hangup" and line.said == [] and seen == []


def test_lange_meldung_wird_abgewartet() -> None:
    """Spricht die Gegenseite beim Abheben länger als die Wartezeit, fällt der Assistent ihr nicht ins Wort:
    die Vorstellung kommt erst nach dem Ende der Meldung, und die ganze Meldung geht ans Modell."""
    line = Line()
    t, _res, seen = _run(line, [{"say": "Grund.", "end": True}], wait_first=0.3,
                         transcripts=["Hier ist die Werkstatt Beispiel, was kann ich für Sie tun?"])
    started = time.monotonic()
    threading.Thread(target=lambda: line.talk(_speech(1200) + _silence(400), realtime=True), daemon=True).start()
    while not line.said and time.monotonic() - started < 5:
        time.sleep(0.01)
    assert time.monotonic() - started >= 1.2, "erst nach dem Ende der Meldung vorstellen"
    t.join(5)
    assert len(line.said) == 2 and "KI" in line.said[0]
    assert "Werkstatt Beispiel" in seen[0][1]["content"]


def test_meldung_klingt_nicht_in_die_erste_antwort_nach() -> None:
    """Nach der Meldung beginnt das Zuhören frisch: Reste der Meldung (Stille-Zähler, Puffer) zählen nicht mit."""
    line = Line()
    t, res, seen = _run(line, [{"say": "Ich rufe wegen eines Termins an."},
                               {"say": "Danke.", "end": True}], wait_first=0.3,
                        transcripts=["Hallo?", "Gern, Dienstag."])
    threading.Thread(target=lambda: line.talk(_speech(300) + _silence(320), realtime=True), daemon=True).start()
    end = time.monotonic() + 5
    while len(line.said) < 2 and time.monotonic() < end:
        time.sleep(0.01)
    time.sleep(1.6)
    line.talk(_speech(400) + _silence(400))
    t.join(6)
    assert [m[-1]["content"] for m in seen] == ["<gegenseite>Hallo?</gegenseite>", "<gegenseite>Gern, Dienstag.</gegenseite>"]
    assert res["r"].turns == 2


def test_modellfehler_beim_eroeffnen_ist_kein_absturz() -> None:
    line = Line()
    t, res, _ = _run(line, [{"say": ""}, {"say": "Ich rufe wegen eines Termins an.", "end": True}],
                     transcripts=["Ja?"])
    end = time.monotonic() + 5
    while len(line.said) < 2 and time.monotonic() < end:
        time.sleep(0.02)
    time.sleep(1.6)                                         # Rückfrage (langer Text) ist ausgesprochen
    line.talk(_speech(400) + _silence(400))
    t.join(6)
    assert "wiederholen" in line.said[1] or "nicht verstanden" in line.said[1]
    assert res["r"].reason == "assistant_end"


def test_eingehend_unveraendert_ohne_eroeffnung() -> None:
    """Standard (eingehend): Begrüßung, dann zuhören – das Modell spricht nicht von sich aus."""
    from backend.agent.conversation import Conversation
    from backend.agent.prompt import AgentConfig

    line = Line()
    calls: list = []
    conv = Conversation(cfg=AgentConfig("Beispiel GmbH", ""), llm=lambda m: calls.append(m) or '{"say":"x"}',
                        stt=lambda p: "x", say=line.say, frames=line.inbox, hangup=line.hung_up.is_set,
                        no_input_ms=800, max_seconds=3, end_silence_ms=300)
    t = threading.Thread(target=conv.run, daemon=True)
    t.start()
    time.sleep(0.5)
    line.hung_up.set()
    t.join(3)
    assert calls == [] and "Wie kann ich Ihnen helfen" in line.said[0]
