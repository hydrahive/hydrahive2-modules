"""OpenRouter-SSE-Stream für Audio auswerten (Chat-Completions mit ``modalities: [text, audio]``).

Lyria liefert das Audio als EINE mehrere MB große ``data:``-Zeile; deshalb werden Bytes selbst an ``\\n`` getrennt
(wie ``read_audio_sse`` im Kern). Neben dem Audio wird gesammelt, was für Diagnose und Liedtext gebraucht wird:
Generierungs-ID, ``finish_reason``, ``delta.content`` und Fehler-Objekte, die OpenRouter nach dem HTTP-200 im Stream
schickt.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field


@dataclass
class StreamResult:
    audio: list[str] = field(default_factory=list)
    text: list[str] = field(default_factory=list)
    done: bool = False
    gen_id: str = ""
    finish: str = ""
    native_finish: str = ""
    errors: list[str] = field(default_factory=list)
    lines: int = 0

    def summary(self) -> str:
        """Kurzer Befund für Meldung und Protokoll (ohne Audio-Daten)."""
        bits = [f"id={self.gen_id or '–'}", f"finish={self.finish or '–'}"]
        if self.native_finish and self.native_finish.lower() != self.finish.lower():
            bits.append(f"native={self.native_finish}")
        bits.append(f"[DONE]={'ja' if self.done else 'nein'}")
        return ", ".join(bits)

    def text_head(self, n: int = 160) -> str:
        return "".join(self.text).strip().replace("\n", " / ")[:n]


def parse_line(line: str, res: StreamResult) -> None:
    if not line.startswith("data:"):
        return
    payload = line[5:].strip()
    if payload == "[DONE]":
        res.done = True
        return
    try:
        obj = json.loads(payload)
    except ValueError:
        return
    if not isinstance(obj, dict):
        return
    res.lines += 1
    res.gen_id = res.gen_id or str(obj.get("id") or "")
    err = obj.get("error")
    if err:
        if isinstance(err, dict):
            res.errors.append(f"{err.get('code', '')} {err.get('message', '')}".strip())
        else:
            res.errors.append(str(err))
    choice = (obj.get("choices") or [{}])[0] or {}
    res.finish = str(choice.get("finish_reason") or res.finish or "")
    res.native_finish = str(choice.get("native_finish_reason") or res.native_finish or "")
    delta = choice.get("delta") or {}
    audio = delta.get("audio")
    if isinstance(audio, dict) and audio.get("data"):
        res.audio.append(audio["data"])
    if isinstance(delta.get("content"), str):
        res.text.append(delta["content"])


async def read_stream(resp) -> StreamResult:
    res = StreamResult()
    buf = b""
    async for chunk in resp.aiter_bytes():
        buf += chunk
        while b"\n" in buf:
            line, buf = buf.split(b"\n", 1)
            parse_line(line.decode("utf-8", "replace").rstrip("\r"), res)
    if buf:
        parse_line(buf.decode("utf-8", "replace"), res)
    return res
