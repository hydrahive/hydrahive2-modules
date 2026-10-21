"""Rohmail → Kopfdaten, Text, Anhänge, Thread-Schlüssel (PLAN-M1 Schritt 4).

Nie eine Ausnahme: kaputte Mails liefern so viel wie möglich und ein `error`. Text für Index/Agenten ist begrenzt.
"""
from __future__ import annotations

import email
import email.policy
import hashlib
import re
from dataclasses import dataclass, field
from datetime import timezone
from email.message import EmailMessage
from email.utils import parsedate_to_datetime

from . import threads
from .htmltext import to_text

BODY_MAX = 200_000
SNIPPET_MAX = 200
HEADER_MAX = 998
_CTRL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")
_MSGID = re.compile(r"<[^<>\s]{1,500}>")


@dataclass
class Parsed:
    sha256: str
    message_id: str = ""
    in_reply_to: str = ""
    thread_key: str = ""
    date: str = ""
    from_addr: str = ""
    to_addr: str = ""
    cc_addr: str = ""
    subject: str = ""
    body: str = ""
    snippet: str = ""
    has_html: bool = False
    attachments: list[dict] = field(default_factory=list)
    error: str = ""

    @property
    def has_attachments(self) -> bool:
        return any(not a["inline"] for a in self.attachments)


def _hdr(msg: EmailMessage, name: str) -> str:
    try:
        v = msg.get(name)
        v = "" if v is None else str(v)
    except (ValueError, TypeError, IndexError, AttributeError):
        v = str(msg.get_all(name, [""])[0] or "") if msg.get_all(name) else ""
    return _CTRL.sub("", re.sub(r"\s+", " ", v)).strip()[:HEADER_MAX]


def _date(msg: EmailMessage) -> str:
    raw = _hdr(msg, "Date")
    try:
        d = parsedate_to_datetime(raw)
    except (TypeError, ValueError, IndexError):
        return ""
    if d is None:
        return ""
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _first_id(value: str) -> str:
    m = _MSGID.search(value)
    return m.group(0) if m else ""


def _part_text(part) -> str:
    try:
        return part.get_content()
    except (LookupError, KeyError, ValueError, AssertionError, AttributeError):
        payload = part.get_payload(decode=True) or b""
        return payload.decode(part.get_content_charset() or "latin-1", errors="replace")


def _walk(msg: EmailMessage, p: Parsed) -> None:
    plain, html, index = [], [], 0
    for part in msg.walk():
        if part.is_multipart():
            continue
        ctype = part.get_content_type()
        disp = (part.get_content_disposition() or "").lower()
        filename = part.get_filename()
        cid = (part.get("Content-ID") or "").strip().strip("<>")
        if filename or disp == "attachment" or (cid and not ctype.startswith("text/")):
            data = part.get_payload(decode=True) or b""
            p.attachments.append({"index": index, "name": _CTRL.sub("", filename or "anhang")[:200], "type": ctype,
                                  "size": len(data), "inline": disp != "attachment" and bool(cid), "cid": cid[:200]})
            index += 1
        elif ctype == "text/plain":
            plain.append(_part_text(part))
        elif ctype == "text/html":
            html.append(_part_text(part))
    p.has_html = bool(html)
    text = "\n\n".join(t for t in plain if t.strip()) or "\n\n".join(to_text(h) for h in html)
    p.body = text.strip()[:BODY_MAX]


def parse(raw: bytes) -> Parsed:
    p = Parsed(sha256=hashlib.sha256(raw or b"").hexdigest())
    try:
        msg = email.message_from_bytes(raw or b"", policy=email.policy.default)
        p.subject, p.from_addr = _hdr(msg, "Subject"), _hdr(msg, "From")
        p.to_addr, p.cc_addr = _hdr(msg, "To"), _hdr(msg, "Cc")
        p.message_id = _first_id(_hdr(msg, "Message-ID"))
        p.in_reply_to = _first_id(_hdr(msg, "In-Reply-To"))
        p.date = _date(msg)
        refs = _MSGID.findall(_hdr(msg, "References"))
        root = refs[0] if refs else p.in_reply_to
        p.thread_key = threads.key(root, p.subject, p.message_id) or "sha:" + p.sha256[:32]
        _walk(msg, p)
    except Exception as e:  # noqa: BLE001 - eine kaputte Mail darf den Abgleich nie stoppen
        p.error = f"{type(e).__name__}: {e}"[:300]
        if not p.thread_key:
            p.thread_key = "sha:" + p.sha256[:32]
    p.snippet = re.sub(r"\s+", " ", p.body)[:SNIPPET_MAX].strip()
    return p
