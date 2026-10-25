"""Gesprächsschleife des Telefon-Agenten mit Fake-Whisper/-Modell/-Piper (PLAN-AGENT-2B Schritt 4).

Ton geht als 20-ms-PCM-Rahmen hinein, gesprochen wird über eine Fake-„say“-Funktion. Zeit läuft echt, aber kurz.
"""
from __future__ import annotations

import json
import math
import queue
import struct
import threading
import time


def _speech(ms: int, level: int = 5000) -> list[bytes]:
    return [struct.pack("<160h", *(int(level * math.sin(2 * math.pi * 220 * n / 8000)) for n in range(160)))
            for _ in range(ms // 20)]


def _silence(ms: int) -> list[bytes]:
    return [b"\x00\x00" * 160 for _ in range(ms // 20)]


class Line:
    """Leitung zum Test: Ton vom Anrufer (Queue) und was HydraHive sagt."""

    def __init__(self) -> None:
        self.inbox: queue.Queue[bytes | None] = queue.Queue()
        self.said: list[str] = []
        self.stopped_speaking = 0
        self.hung_up = threading.Event()

    def talk(self, frames, *, realtime: bool = False) -> None:
        for f in frames:
            self.inbox.put(f)
            if realtime:
                time.sleep(0.02)

    def say(self, text: str, interrupted) -> bool:
        """HydraHive spricht: 'Abspielen' dauert 0,2 s (lange Texte 1,5 s), kann unterbrochen werden."""
        self.said.append(text)
        end = time.monotonic() + (1.5 if len(text) > 40 else 0.2)
        while time.monotonic() < end:
            if interrupted():
                self.stopped_speaking += 1
                return False
            time.sleep(0.01)
        return True


def _run(line: Line, replies, *, transcripts=None, **kw):
    from backend.agent.conversation import Conversation
    from backend.agent.prompt import AgentConfig

    replies = list(replies)
    transcripts = list(transcripts or [])
    seen_msgs: list[list[dict]] = []

    def llm(messages):
        seen_msgs.append(messages)
        r = replies.pop(0) if replies else {"say": "Auf Wiederhören!", "end": True}
        if isinstance(r, Exception):
            raise r
        return r if isinstance(r, str) else json.dumps(r, ensure_ascii=False)

    def stt(pcm16k: bytes) -> str:
        assert len(pcm16k) % 2 == 0
        t = transcripts.pop(0) if transcripts else "Hallo"
        if isinstance(t, Exception):
            raise t
        return t

    opts = {"no_input_ms": 1500, "max_seconds": 10, "end_silence_ms": 300, "thinking_after": 5.0}
    opts.update(kw)
    conv = Conversation(cfg=AgentConfig("Beispiel GmbH", "Öffnungszeiten: Mo–Fr 9–17 Uhr."), llm=llm, stt=stt,
                        say=line.say, frames=line.inbox, hangup=line.hung_up.is_set, **opts)
    result = {}
    t = threading.Thread(target=lambda: result.update(r=conv.run()), daemon=True)
    t.start()
    return conv, t, result, seen_msgs


def test_begruessung_frage_antwort_verabschiedung() -> None:
    line = Line()
    _conv, t, res, msgs = _run(line, [
        {"say": "Wir haben Montag bis Freitag von 9 bis 17 Uhr geöffnet.", "notes": {"concern": "Öffnungszeiten"}},
        {"say": "Gern geschehen, auf Wiederhören!", "notes": {"summary": "Fragte nach Öffnungszeiten."}, "end": True},
    ], transcripts=["Wann haben Sie geöffnet?", "Danke, tschüss."])
    time.sleep(0.3)
    line.talk(_speech(500) + _silence(400))
    time.sleep(0.6)
    line.talk(_speech(500) + _silence(400))
    t.join(5)
    r = res["r"]
    assert "KI" in line.said[0] and "Beispiel GmbH" in line.said[0], "feste Begrüßung zuerst"
    assert line.said[1:] == ["Wir haben Montag bis Freitag von 9 bis 17 Uhr geöffnet.", "Gern geschehen, auf Wiederhören!"]
    assert r.reason == "assistant_end" and r.turns == 2
    assert r.notes["concern"] == "Öffnungszeiten" and r.notes["summary"] == "Fragte nach Öffnungszeiten."
    assert "<anrufer>Wann haben Sie geöffnet?</anrufer>" in msgs[0][-1]["content"]


def test_auflegen_beendet_sofort() -> None:
    line = Line()
    _conv, t, res, _ = _run(line, [])
    time.sleep(0.3)
    line.hung_up.set()
    t.join(2)
    assert not t.is_alive() and res["r"].reason == "caller_hangup"


def test_dazwischenreden_stoppt_die_eigene_rede() -> None:
    line = Line()
    long_say = {"say": "Lange Antwort " * 5}
    _conv, t, res, _ = _run(line, [long_say, {"say": "Ja?", "end": True}], transcripts=["Frage", "Stopp, andere Frage"])
    time.sleep(0.3)
    line.talk(_speech(400) + _silence(400))
    deadline = time.monotonic() + 3
    while len(line.said) < 2 and time.monotonic() < deadline:
        time.sleep(0.01)
    line.talk(_speech(400), realtime=True)                     # redet in die Antwort hinein
    line.talk(_silence(400))
    t.join(5)
    assert line.stopped_speaking >= 1, "eigene Rede wurde abgebrochen"
    assert res["r"].turns == 2


def test_schweigen_einmal_nachfragen_dann_verabschieden() -> None:
    line = Line()
    _conv, t, res, _ = _run(line, [], no_input_ms=400)
    line.talk(_silence(3000))                                 # auch ohne weiteren Ton endet das Warten nach Uhrzeit
    t.join(6)
    r = res["r"]
    assert r.reason == "no_input"
    assert any("noch da" in s for s in line.said) and "Wiederhören" in line.said[-1]


def test_drei_fehler_hintereinander_technische_entschuldigung() -> None:
    line = Line()
    _conv, t, res, _ = _run(line, [RuntimeError("weg")] * 3, transcripts=["a", "b", "c"])
    time.sleep(0.3)
    for _ in range(3):
        line.talk(_speech(400) + _silence(400))
        time.sleep(0.5)
    t.join(6)
    assert res["r"].reason == "errors" and "technische Probleme" in line.said[-1]


def test_whisper_versteht_nichts_kurze_rueckfrage() -> None:
    line = Line()
    _conv, t, res, msgs = _run(line, [{"say": "Gut.", "end": True}], transcripts=["", "Hallo"])
    time.sleep(0.3)
    line.talk(_speech(400) + _silence(400))
    time.sleep(0.6)
    line.talk(_speech(400) + _silence(400))
    t.join(5)
    assert any("wiederholen" in s for s in line.said)
    assert len(msgs) == 1, "leere Erkennung geht nicht ans Modell"
    assert res["r"].reason == "assistant_end" and res["r"].turns == 1


def test_hoechstdauer() -> None:
    line = Line()
    _conv, t, res, _ = _run(line, [{"say": "Mhm."}] * 50, transcripts=["x"] * 50, max_seconds=1.5)
    time.sleep(0.3)
    line.talk((_speech(300) + _silence(400)) * 10, realtime=True)
    t.join(4)
    assert res["r"].reason == "max_duration" and "Wiederhören" in line.said[-1]


def test_kaputte_modellantwort_wird_rueckfrage_kein_absturz() -> None:
    line = Line()
    _conv, t, res, _ = _run(line, ["kein json", {"say": "Okay, tschüss.", "end": True}], transcripts=["a", "b"])
    time.sleep(0.3)
    line.talk(_speech(400) + _silence(400))
    time.sleep(0.6)
    line.talk(_speech(400) + _silence(400))
    t.join(5)
    assert "wiederholen" in line.said[1] and res["r"].reason == "assistant_end"


def test_verlauf_bleibt_nur_im_speicher_und_ton_wird_nicht_gesammelt() -> None:
    line = Line()
    _conv, t, res, _ = _run(line, [{"say": "Ok.", "end": True}], transcripts=["Mein Name ist Max"])
    time.sleep(0.3)
    line.talk(_speech(400) + _silence(400))
    t.join(5)
    r = res["r"]
    assert not hasattr(r, "audio") and not hasattr(r, "history"), "Ergebnis enthält weder Ton noch Wortlaut"
    assert set(vars(r)) == {"reason", "turns", "notes", "seconds"}


def test_denkpause_kurzes_einen_moment() -> None:
    """Braucht das Modell länger als thinking_after, sagt der Agent „Einen Moment.“ – danach kommt die Antwort."""
    line = Line()
    slow = [json.dumps({"say": "Fertig.", "end": True})]

    def slow_llm(messages):
        time.sleep(0.6)
        return slow.pop(0)
    conv, t, res, _ = _run(line, [], transcripts=["a"], thinking_after=0.2)
    conv._llm = slow_llm
    time.sleep(0.3)
    line.talk(_speech(400) + _silence(400))
    t.join(5)
    assert line.said[-2:] == ["Einen Moment.", "Fertig."] and res["r"].reason == "assistant_end"


def test_schnelles_modell_ohne_einen_moment() -> None:
    line = Line()
    _conv, t, res, _ = _run(line, [{"say": "Fertig.", "end": True}], transcripts=["a"], thinking_after=1.0)
    time.sleep(0.3)
    line.talk(_speech(400) + _silence(400))
    t.join(5)
    assert "Einen Moment." not in line.said and res["r"].reason == "assistant_end"
