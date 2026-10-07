"""Denktext von Reasoning-Modellen entfernen (``<think>…</think>``, ``<thinking>…</thinking>``).

Manche Modelle (Qwen, DeepSeek u. a. über Ollama/OpenRouter) liefern ihr Nachdenken im normalen Text. Das darf
nie ins Buch. ``ThinkFilter`` arbeitet auf einem Strom: Er gibt nur sichtbaren Text weiter und hält zurück, solange
ein Denkblock offen ist oder am Ende eines Stücks ein Tag beginnen könnte. Ein nicht geschlossener Block (Modell
bricht wegen max_tokens ab) wird verworfen.
"""
from __future__ import annotations

import re

_OPEN = re.compile(r"<think(?:ing)?>", re.IGNORECASE)
_CLOSE = re.compile(r"</think(?:ing)?>", re.IGNORECASE)
_OPEN_TAGS = ("<think>", "<thinking>")
_CLOSE_TAGS = ("</think>", "</thinking>")


def _partial_tag(buf: str, tags: tuple[str, ...]) -> str:
    """Ende von ``buf``, das der Anfang eines Tags sein könnte (ab dem letzten „<“), sonst ""."""
    i = buf.rfind("<")
    if i < 0:
        return ""
    tail = buf[i:].lower()
    return buf[i:] if any(t.startswith(tail) and t != tail for t in tags) else ""


class ThinkFilter:
    def __init__(self) -> None:
        self._buf = ""
        self._inside = False

    def feed(self, piece: str) -> str:
        self._buf += piece
        out = []
        while True:
            if self._inside:
                m = _CLOSE.search(self._buf)
                if not m:
                    self._buf = _partial_tag(self._buf, _CLOSE_TAGS)   # Denktext verwerfen
                    return "".join(out)
                self._buf, self._inside = self._buf[m.end():], False
            else:
                m = _OPEN.search(self._buf)
                if not m:
                    keep = _partial_tag(self._buf, _OPEN_TAGS)
                    out.append(self._buf[:len(self._buf) - len(keep)])
                    self._buf = keep
                    return "".join(out)
                out.append(self._buf[:m.start()])
                self._buf, self._inside = self._buf[m.end():], True

    def end(self) -> str:
        """Rest nach dem letzten Stück: zurückgehaltener Text, offener Denkblock fällt weg."""
        rest, self._buf = ("" if self._inside else self._buf), ""
        return rest


def strip_think(text: str) -> str:
    f = ThinkFilter()
    return f.feed(text or "") + f.end()
