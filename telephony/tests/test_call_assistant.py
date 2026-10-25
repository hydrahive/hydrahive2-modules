"""Anruf im Modus „Telefon-Assistent“: Ton des Anrufers kommt bei der Gesprächsschleife an, Antworten gehen als RTP
zurück, Dazwischenreden stoppt die Ausgabe (PLAN-AGENT-2B Schritt 5). Echter Test-Anrufer, Fakes für die Dienste.
"""
from __future__ import annotations

import json
import math
import struct
import time

from _fake_caller import FakeCaller
from test_call import Hydra, _wait


def _tone_pcma(ms: int, level: int = 6000) -> bytes:
    from backend.media import g711

    pcm = struct.pack(f"<{ms * 8}h", *(int(level * math.sin(2 * math.pi * 220 * n / 8000)) for n in range(ms * 8)))
    return g711.encode(pcm, "PCMA")


class Assistant:
    """Fake-Dienste: Whisper liefert vorgegebene Sätze, Modell vorgegebene Antworten, Piper 100 ms Ton je Text."""

    def __init__(self, replies, transcripts) -> None:
        self.replies, self.transcripts = list(replies), list(transcripts)
        self.heard: list[int] = []
        self.caller_numbers: list[str] = []
        self.spoken: list[str] = []

    def stt(self, pcm16k: bytes) -> str:
        self.heard.append(len(pcm16k))
        return self.transcripts.pop(0) if self.transcripts else ""

    def llm(self, messages) -> str:
        sysmsg = messages[0]["content"]
        self.caller_numbers.append(sysmsg.split("(nicht überprüft): ")[1].split("\n")[0])
        assert "0301234567" not in sysmsg
        return json.dumps(self.replies.pop(0) if self.replies else {"say": "Tschüss.", "end": True})

    def tts(self, text: str, codec: str) -> bytes:
        self.spoken.append(text)
        return b"\x22" * 800                                          # 100 ms


def _hydra(assistant: Assistant) -> Hydra:
    from backend.agent.prompt import AgentConfig

    h = Hydra(answer="Hallo")
    h.d.assistant = lambda: {"cfg": AgentConfig("Beispiel GmbH", "Öffnungszeiten: Mo–Fr 9–17 Uhr."),
                             "llm": assistant.llm, "stt": assistant.stt, "tts": assistant.tts,
                             "options": {"no_input_ms": 3000, "end_silence_ms": 300, "thinking_after": 5.0}}
    return h


def _send_voice(caller: FakeCaller, port: int, audio: bytes) -> None:
    from backend.media import rtp

    for i in range(0, len(audio), 160):
        caller.rtp.sendto(rtp.packet(payload_type=8, seq=1000 + i // 160, timestamp=i, ssrc=9,
                                     payload=audio[i:i + 160]), ("127.0.0.1", port))
        time.sleep(0.02)


def _media_port(caller: FakeCaller) -> int:
    ok = next(r for r in caller.responses if r.status == 200 and "INVITE" in r.header("cseq"))
    return int(ok.body.split(b"m=audio ")[1].split(b" ")[0])


def test_gespraech_ueber_echte_leitung() -> None:
    a = Assistant([{"say": "Montag bis Freitag von 9 bis 17 Uhr.", "notes": {"concern": "Öffnungszeiten"}},
                   {"say": "Auf Wiederhören!", "notes": {"name": "Max Mustermann"}, "end": True}],
                  ["Wann haben Sie geöffnet?", "Danke, Max Mustermann, tschüss."])
    h = _hydra(a)
    c = FakeCaller(send_rtp=False)
    try:
        c.invite(h.addr)
        assert _wait(lambda: 200 in c.statuses())
        port = _media_port(c)
        assert _wait(lambda: len(c.rtp_packets) >= 5), "Begrüßung kommt als Ton an"
        _send_voice(c, port, _tone_pcma(600) + bytes([0xD5]) * 8 * 500)
        assert _wait(lambda: len(a.spoken) >= 2, timeout=5)
        _send_voice(c, port, _tone_pcma(600) + bytes([0xD5]) * 8 * 500)
        assert _wait(lambda: h.records, timeout=8)
        rec = h.records[0]
        assert rec["result"] == "assistant_end" and rec["turns"] == 2
        assert a.caller_numbers and set(a.caller_numbers) == {"•••567"}, "Modell sieht nur die maskierte Nummer"
        assert rec["notes"] == {"concern": "Öffnungszeiten", "name": "Max Mustermann"}
        assert "KI" in a.spoken[0] and a.spoken[1:] == ["Montag bis Freitag von 9 bis 17 Uhr.", "Auf Wiederhören!"]
        assert all(n > 0 and n % 2 == 0 for n in a.heard), "Whisper bekommt 16-kHz-PCM"
        assert "BYE" in [r.method for r in c.requests], "HydraHive legt nach der Verabschiedung auf"
    finally:
        c.close()
        h.close()


def test_anrufer_legt_auf_gespraech_endet() -> None:
    a = Assistant([], [])
    h = _hydra(a)
    c = FakeCaller(send_rtp=False)
    try:
        c.invite(h.addr)
        assert _wait(lambda: len(c.rtp_packets) >= 2)
        c.bye()
        assert _wait(lambda: h.records, timeout=5)
        assert h.records[0]["result"] == "caller_hangup"
    finally:
        c.close()
        h.close()


def test_ohne_assistent_bleibt_es_bei_der_ansage() -> None:
    """Modus „Nur Ansage“: assistant() liefert None → Verhalten wie 2a."""
    h = Hydra(answer="Hallo")
    h.d.assistant = lambda: None
    c = FakeCaller()
    try:
        c.invite(h.addr)
        assert _wait(lambda: h.records)
        assert h.records[0]["result"] == "answered" and "turns" not in h.records[0]
    finally:
        c.close()
        h.close()


def test_ton_von_fremder_adresse_erreicht_das_gespraech_nicht() -> None:
    import socket

    a = Assistant([{"say": "x", "end": True}], ["sollte nie kommen"])
    h = _hydra(a)
    c = FakeCaller(send_rtp=False)
    evil = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        body = c.sdp().replace(b"c=IN IP4 127.0.0.1", b"c=IN IP4 127.0.0.2")
        c.invite(h.addr, body=body)
        assert _wait(lambda: 200 in c.statuses())
        port = _media_port(c)
        from backend.media import rtp
        audio = _tone_pcma(800) + bytes([0xD5]) * 8 * 500
        for i in range(0, len(audio), 160):
            evil.sendto(rtp.packet(payload_type=8, seq=i, timestamp=i, ssrc=1, payload=audio[i:i + 160]),
                        ("127.0.0.1", port))
            time.sleep(0.02)
        time.sleep(0.5)
        assert a.heard == [], "fremder Ton wird verworfen"
        c.bye()
        assert _wait(lambda: h.records, timeout=5)
    finally:
        evil.close()
        c.close()
        h.close()
