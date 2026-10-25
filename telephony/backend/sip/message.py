"""SIP-Nachrichten lesen und bauen (RFC 3261 §7, §20).

Bewusst klein: Startzeile, Kopfzeilen (inkl. Kurzformen), Text-Körper. Alles Fremde, Kaputte oder Übergroße wird mit
ParseError abgelehnt. Beim Bauen sind Zeilenumbrüche in Werten verboten (keine eingeschleusten Kopfzeilen).
"""
from __future__ import annotations

from dataclasses import dataclass, field

MAX_SIZE = 65507
_COMPACT = {"v": "via", "f": "from", "t": "to", "i": "call-id", "m": "contact", "l": "content-length",
            "c": "content-type", "k": "supported", "e": "content-encoding", "s": "subject"}
_COPY = ("via", "from", "call-id", "cseq")


class ParseError(ValueError):
    pass


@dataclass
class Message:
    is_request: bool
    method: str = ""
    uri: str = ""
    status: int = 0
    reason: str = ""
    headers: list[tuple[str, str]] = field(default_factory=list)
    body: bytes = b""

    def headers_all(self, name: str) -> list[str]:
        key = _norm(name)
        return [v for k, v in self.headers if k == key]

    def header(self, name: str) -> str | None:
        vals = self.headers_all(name)
        return vals[0] if vals else None


def _norm(name: str) -> str:
    n = name.strip().lower()
    return _COMPACT.get(n, n)


def parse(raw: bytes) -> Message:
    if not raw or len(raw) > MAX_SIZE:
        raise ParseError("leer oder zu groß")
    head, sep, body = raw.partition(b"\r\n\r\n")
    if not sep:
        raise ParseError("Kopf nicht abgeschlossen")
    try:
        lines = head.decode("utf-8").split("\r\n")
    except UnicodeDecodeError as e:
        raise ParseError("kein UTF-8") from e
    start = lines[0].split(" ", 2)
    if len(start) < 3:
        raise ParseError("Startzeile kaputt")
    if start[0] == "SIP/2.0":
        if not (start[1].isdigit() and len(start[1]) == 3):
            raise ParseError("Statuscode kaputt")
        msg = Message(is_request=False, status=int(start[1]), reason=start[2])
    elif start[2] == "SIP/2.0" and start[0].isalpha() and start[0].isupper():
        msg = Message(is_request=True, method=start[0], uri=start[1])
    else:
        raise ParseError("keine SIP-Nachricht")
    for line in lines[1:]:
        if line[:1] in (" ", "\t") and msg.headers:          # Fortsetzungszeile
            k, v = msg.headers[-1]
            msg.headers[-1] = (k, f"{v} {line.strip()}")
            continue
        name, colon, value = line.partition(":")
        if not colon or not name.strip():
            raise ParseError("Kopfzeile kaputt")
        msg.headers.append((_norm(name), value.strip()))
    msg.body = body
    return msg


def _line(name: str, value: str) -> str:
    if any(ch in value or ch in name for ch in "\r\n\0"):
        raise ValueError("Zeilenumbruch in SIP-Kopfzeile")
    return f"{name}: {value}\r\n"


def _finish(first: str, headers: list[tuple[str, str]], body: bytes) -> bytes:
    text = first + "".join(_line(k, v) for k, v in headers) + _line("Content-Length", str(len(body))) + "\r\n"
    return text.encode() + body


def build_request(method: str, uri: str, headers: list[tuple[str, str]], body: bytes = b"") -> bytes:
    if any(ch in uri or ch in method for ch in " \r\n\0"):
        raise ValueError("ungültige Startzeile")
    return _finish(f"{method} {uri} SIP/2.0\r\n", headers, body)


def build_response(req: Message, status: int, reason: str, *, to_tag: str | None = None,
                   extra: list[tuple[str, str]] = (), body: bytes = b"") -> bytes:
    """Antwort auf eine Anfrage: Via/From/Call-ID/CSeq übernehmen, To ggf. mit eigenem Tag (RFC 3261 §8.2.6)."""
    headers: list[tuple[str, str]] = []
    for key in _COPY:
        for v in req.headers_all(key):
            headers.append((key.title() if key != "call-id" else "Call-ID", v))
            if key == "from":
                to = req.header("to") or ""
                if to_tag and ";tag=" not in to:
                    to = f"{to};tag={to_tag}"
                headers.append(("To", to))
    headers.extend(extra)
    return _finish(f"SIP/2.0 {status} {reason}\r\n", headers, body)
