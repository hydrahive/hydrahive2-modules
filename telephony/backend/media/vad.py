"""Sprache/Stille je 20-ms-Rahmen erkennen (PLAN-AGENT-2B): wann redet der Anrufer, wann ist der Satz zu Ende.

Einfach und robust statt Modell: Lautstärke (RMS) gegen eine Schwelle, die das Grundrauschen der Leitung mitlernt.
Ereignisse:
- ``speech_start``: Anrufer beginnt zu sprechen (mind. ``min_speech_ms`` am Stück)
- ``utterance``:   Satz zu Ende (``end_silence_ms`` Stille) oder zu lang – mit dem Ton der ganzen Äußerung
- ``barge_in``:    Anrufer redet dazwischen, während HydraHive spricht (``speaking`` = True)
- ``no_input``:    seit ``no_input_ms`` nichts gesagt (einmal je Abschnitt, ``reset()`` startet neu)
"""
from __future__ import annotations

import math
from dataclasses import dataclass

FRAME_BYTES = 320                            # 160 Werte à 16 Bit = 20 ms bei 8 kHz
FRAME_MS = 20


def rms(pcm: bytes) -> float:
    s = memoryview(pcm).cast("h")
    return math.sqrt(sum(v * v for v in s) / len(s)) if len(s) else 0.0


@dataclass
class VadEvent:
    kind: str
    pcm: bytes = b""


class Vad:
    def __init__(self, *, end_silence_ms: int = 700, min_speech_ms: int = 100, max_utterance_ms: int = 20000,
                 no_input_ms: int = 8000, barge_in_ms: int = 300, pre_roll_ms: int = 200) -> None:
        self.end_frames = end_silence_ms // FRAME_MS
        self.min_frames = max(1, min_speech_ms // FRAME_MS)
        self.max_frames = max_utterance_ms // FRAME_MS
        self.no_input_frames = no_input_ms // FRAME_MS
        self.barge_frames = max(1, barge_in_ms // FRAME_MS)
        self.pre_frames = pre_roll_ms // FRAME_MS
        self.noise = 100.0                       # gelerntes Grundrauschen (RMS)
        self.speaking = False                    # HydraHive spricht gerade (für Barge-in)
        self.reset()

    def reset(self) -> None:
        self._buf: list[bytes] = []
        self._pre: list[bytes] = []
        self._in_speech = False
        self._loud_run = self._quiet_run = self._idle = self._barge_run = 0
        self._no_input_sent = False

    @property
    def in_speech(self) -> bool:
        return self._in_speech

    def _threshold(self) -> float:
        return max(400.0, self.noise * 3.0)

    def feed(self, frame: bytes) -> list[VadEvent]:
        if len(frame) != FRAME_BYTES:
            return []
        level = rms(frame)
        loud = level > self._threshold()
        if not loud and not self._in_speech:
            self.noise = 0.95 * self.noise + 0.05 * level          # Rauschen nur in Pausen mitlernen
        out: list[VadEvent] = []

        if self.speaking:
            self._barge_run = self._barge_run + 1 if level > self._threshold() * 1.5 else 0
            if self._barge_run >= self.barge_frames:
                self._barge_run = 0
                out.append(VadEvent("barge_in"))
        else:
            self._barge_run = 0

        if not self._in_speech:
            self._pre = (self._pre + [frame])[-(self.pre_frames + self.min_frames):]
            self._loud_run = self._loud_run + 1 if loud else 0
            if self._loud_run >= self.min_frames:
                self._in_speech, self._buf, self._quiet_run, self._idle = True, list(self._pre), 0, 0
                out.append(VadEvent("speech_start"))
            elif not self.speaking:
                self._idle += 1
                if self._idle >= self.no_input_frames and not self._no_input_sent:
                    self._no_input_sent = True
                    out.append(VadEvent("no_input"))
            return out

        self._buf.append(frame)
        self._quiet_run = 0 if loud else self._quiet_run + 1
        if self._quiet_run >= self.end_frames or len(self._buf) >= self.max_frames:
            keep = self._buf[: len(self._buf) - min(self._quiet_run, self.end_frames)] or self._buf
            out.append(VadEvent("utterance", b"".join(keep)))
            noise = self.noise
            self.reset()
            self.noise = noise
        return out
