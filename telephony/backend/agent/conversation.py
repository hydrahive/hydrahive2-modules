"""Gesprächsschleife des Telefon-Agenten (PLAN-AGENT-2B): zuhören → verstehen → antworten → sprechen.

Läuft im Anruf-Thread. Die drei Dienste kommen als Funktionen herein (Whisper, Sprachmodell, Sprechen), damit sie
austauschbar und testbar sind. Der Gesprächstext lebt nur in diesem Objekt; zurückgegeben wird allein das Ergebnis
mit Notiz – kein Ton, kein Wortlaut.
"""
from __future__ import annotations

import logging
import queue
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field

from ..media import g711
from ..media.vad import Vad
from . import phrases as P
from .opening import OPENING_SILENT, hello  # noqa: F401 - OPENING_SILENT Teil der Schnittstelle
from .prompt import AgentConfig, build_messages, greeting
from .reply import parse_reply

logger = logging.getLogger(__name__)
MAX_ERRORS = 3
ASSISTANT_MAX_SECONDS = 300   # Höchstdauer eines Gesprächs (PLAN-AGENT-2B: 5 Minuten, fest) – die Ansage hat ihre eigene


@dataclass
class ConversationResult:
    reason: str
    turns: int = 0
    notes: dict = field(default_factory=dict)
    seconds: float = 0.0


class Conversation:
    def __init__(self, *, cfg: AgentConfig, llm: Callable[[list[dict]], str], stt: Callable[[bytes], str],
                 say: Callable[[str, Callable[[], bool]], bool], frames: queue.Queue[bytes | None],
                 hangup: Callable[[], bool], max_seconds: float = ASSISTANT_MAX_SECONDS, no_input_ms: int = 8000,
                 end_silence_ms: int = 700, thinking_after: float = 1.5, messages: Callable | None = None,
                 greet: Callable | None = None, opening: bool = False, wait_first: float = 2.0) -> None:
        # messages/greet: eigener Systemtext + Begrüßung; opening: ausgehend (agent/opening.py, prompt_out.py)
        self.cfg, self._llm, self._stt, self._say = cfg, llm, stt, say
        self._messages, self._greet = messages or build_messages, greet or greeting
        self._opening, self._wait_first = opening, wait_first
        self._frames, self._hangup = frames, hangup
        self._max, self._thinking_after = max_seconds, thinking_after
        self.vad = Vad(end_silence_ms=end_silence_ms, no_input_ms=no_input_ms)
        self._no_input_s = no_input_ms / 1000
        self._history: list[tuple[str, str]] = []
        self._notes: dict = {}
        self._start = time.monotonic()
        self._barge = threading.Event()

    # ---- Hilfen ----
    def _over(self) -> bool:
        return time.monotonic() - self._start >= self._max

    def _drain(self) -> None:
        """Ton während eigener Rede auf Dazwischenreden prüfen (läuft parallel zum Sprechen)."""
        while self.vad.speaking and not self._hangup():
            try:
                f = self._frames.get(timeout=0.05)
            except queue.Empty:
                continue
            if f is None:
                return
            if any(e.kind == "barge_in" for e in self.vad.feed(f)):
                self._barge.set()
                return

    def _speak(self, text: str) -> bool:
        """Sprechen; True = ganz gesprochen, False = unterbrochen (Barge-in) oder aufgelegt."""
        self._barge.clear()
        self.vad.speaking = True
        watcher = threading.Thread(target=self._drain, daemon=True)
        watcher.start()
        try:
            done = self._say(text, lambda: self._barge.is_set() or self._hangup())
        finally:
            self.vad.speaking = False
            watcher.join(0.3)
        self.vad.reset()
        return done

    def _listen(self) -> tuple[str, bytes]:
        """Wartet auf: ("utterance", ton) | ("no_input", b"") | ("hangup", b"") | ("timeout", b"").

        Schweigen zählt nach Uhrzeit, nicht nur nach Rahmen – kommt gar kein Ton mehr (Leitung still), endet das
        Warten trotzdem.
        """
        quiet_since = time.monotonic()
        while True:
            if self._hangup():
                return "hangup", b""
            if self._over():
                return "timeout", b""
            try:
                f = self._frames.get(timeout=0.1)
            except queue.Empty:
                if not self.vad.in_speech and time.monotonic() - quiet_since >= self._no_input_s:
                    return "no_input", b""
                continue
            if f is None:
                return "hangup", b""
            for e in self.vad.feed(f):
                if e.kind in ("utterance", "no_input"):
                    return e.kind, e.pcm
                if e.kind == "speech_start":
                    quiet_since = time.monotonic()

    def _think(self, messages: list[dict]) -> str:
        box: dict = {}

        def work():
            try:
                box["v"] = self._llm(messages)
            except Exception as e:  # noqa: BLE001 - jeder Fehler zählt als Fehlversuch
                box["e"] = e
        t = threading.Thread(target=work, daemon=True)
        t.start()
        t.join(self._thinking_after)
        if t.is_alive():
            self._speak(P.SAY_THINKING)
            t.join(30)
        if "e" in box or "v" not in box:
            raise RuntimeError(type(box.get("e")).__name__ if "e" in box else "Zeitüberschreitung")
        return box["v"]

    def _done(self, reason: str, turns: int) -> ConversationResult:
        return ConversationResult(reason=reason, turns=turns, notes=dict(self._notes),
                                  seconds=round(time.monotonic() - self._start, 1))

    # ---- Ablauf ----
    def run(self) -> ConversationResult:
        from .reply import merge_notes

        turns = errors = 0
        asked_still_there = False
        pending: str | None = None                          # ausgehend: Meldung der Gegenseite → Modell eröffnet
        if self._opening:
            pending = hello(self, self._wait_first)
            if pending is None:
                return self._done("caller_hangup", turns)
        self._speak(self._greet(self.cfg))
        while True:
            kind, text, pending = ("opening", pending, None) if pending is not None else ("", "", None)
            if self._hangup():
                return self._done("caller_hangup", turns)
            if kind != "opening":
                kind, pcm = self._listen()
            if kind == "hangup":
                return self._done("caller_hangup", turns)
            if kind == "timeout":
                self._speak(P.SAY_BYE_TIME)
                return self._done("max_duration", turns)
            if kind == "no_input":
                if asked_still_there:
                    self._speak(P.SAY_BYE_SILENT)
                    return self._done("no_input", turns)
                asked_still_there = True
                self._speak(P.SAY_STILL_THERE)
                continue
            asked_still_there = False
            if kind != "opening":
                try:
                    text = self._stt(g711.up_16k(pcm)).strip()
                except Exception as e:  # noqa: BLE001
                    logger.warning("telephony: Spracherkennung fehlgeschlagen (%s)", type(e).__name__)
                    text, errors = "", errors + 1
                pcm = b""                                    # Ton sofort verwerfen
            if not text:
                if errors >= MAX_ERRORS:
                    self._speak(P.SAY_ERRORS)
                    return self._done("errors", turns)
                self._speak(P.SAY_NOT_UNDERSTOOD)
                continue
            self._history.append(("caller", text))
            try:
                reply = parse_reply(self._think(self._messages(self.cfg, self._history)))
                errors = 0 if reply.ok else errors
            except RuntimeError as e:
                logger.warning("telephony: Sprachmodell fehlgeschlagen (%s)", e)
                errors += 1
                if errors >= MAX_ERRORS:
                    self._speak(P.SAY_ERRORS)
                    return self._done("errors", turns)
                self._speak(P.SAY_NOT_UNDERSTOOD)
                continue
            turns += 1
            self._notes = merge_notes(self._notes, reply.notes)
            self._history.append(("assistant", reply.say))
            if self._over():
                self._speak(P.SAY_BYE_TIME)
                return self._done("max_duration", turns)
            self._speak(reply.say)
            if reply.end:
                return self._done("assistant_end", turns)
