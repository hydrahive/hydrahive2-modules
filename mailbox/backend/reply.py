"""Antworten und Weiterleiten (PLAN-M2 Schritt 2). Das Original kommt aus dem Archiv (Rohmail).

Antwort: an Reply-To (sonst From), „Re:“ nur wenn noch kein Antwort-Präfix, In-Reply-To + References für die
Unterhaltung, Zitat mit „Am … schrieb …“. Allen antworten: To + Cc des Originals ohne die eigene Adresse.
Weiterleiten: „WG:“, Kopf des Originals im Text, Anhänge optional mitnehmen.
"""
from __future__ import annotations

import email
import email.policy
import re

from . import addresses, parse

_REPLY_PREFIX = re.compile(r"^\s*(re|aw|antw|sv)\s*(\[\d+\])?\s*:", re.IGNORECASE)
_MSGID = re.compile(r"<[^<>\s]{1,500}>")


def _orig(raw: bytes):
    return email.message_from_bytes(raw, policy=email.policy.default), parse.parse(raw)


def _addr_list(value: str) -> list:
    try:
        return addresses.parse_list(value or "")
    except addresses.AddressError:
        return []                 # kaputte Kopfzeile im Original: lieber leer als falsch


def _without_signature(text: str) -> str:
    """Alles ab der Trennzeile „-- “ (RFC 3676 §4.3) weg – die Signatur des anderen wird nicht mitzitiert."""
    lines = text.splitlines()
    return "\n".join(lines[: lines.index("-- ")] if "-- " in lines else lines).rstrip()


def _quote(p: parse.Parsed) -> str:
    who = p.from_addr or "Unbekannt"
    when = p.date.replace("T", " ").replace("Z", " UTC") if p.date else "einem unbekannten Datum"
    quoted = "\n".join("> " + line for line in _without_signature(p.body or "").splitlines())
    return f"Am {when} schrieb {who}:\n{quoted}"


def _subject(prefix: str, subject: str, *, keep_if: re.Pattern | None) -> str:
    s = (subject or "").strip() or "(ohne Betreff)"
    if keep_if and keep_if.match(s):
        return s
    return f"{prefix} {s}"


def _recipients(acc: dict, msg, p, reply_all: bool):
    from .compose import ComposeError
    target = _addr_list(parse._hdr(msg, "Reply-To")) or _addr_list(p.from_addr)
    if not target:
        raise ComposeError("Original ohne Absender – bitte Empfänger selbst eintragen")
    own = acc["address"]
    to = addresses.without(target, own) or target
    cc = []
    if reply_all:
        seen = {r.addr.lower() for r in to}
        for r in _addr_list(p.to_addr) + _addr_list(p.cc_addr):
            if r.addr.lower() not in seen and r.addr.lower() != own.lower():
                seen.add(r.addr.lower())
                cc.append(r)
    return to, cc


def reply(acc: dict, raw: bytes, *, text: str, reply_all: bool, bcc: str = "", extra_attachments=None):
    from .compose import assemble
    msg, p = _orig(raw)
    to, cc = _recipients(acc, msg, p, reply_all)
    refs = _MSGID.findall(parse._hdr(msg, "References"))
    if p.message_id and p.message_id not in refs:
        refs.append(p.message_id)
    headers = {}
    if p.message_id:
        headers["In-Reply-To"] = p.message_id
    if refs:
        headers["References"] = " ".join(refs[-20:])
    body = f"{(text or '').rstrip()}\n\n{_quote(p)}"
    return assemble(acc, to=to, cc=cc, bcc=_addr_list(bcc), subject=_subject("Re:", p.subject, keep_if=_REPLY_PREFIX),
                    text=body, extra_headers=headers, attachments=extra_attachments)


def _original_attachments(msg) -> list[tuple[str, str, bytes]]:
    out = []
    for part in msg.iter_attachments():
        data = part.get_payload(decode=True) or b""
        out.append((part.get_filename() or "anhang", part.get_content_type(), data))
    return out


def forward(acc: dict, raw: bytes, *, to: str, text: str, with_attachments: bool, cc: str = "", bcc: str = "",
            extra_attachments=None):
    from .compose import build
    msg, p = _orig(raw)
    head = ("---------- Weitergeleitete Nachricht ----------\n"
            f"Von: {p.from_addr}\nDatum: {p.date}\nBetreff: {p.subject}\nAn: {p.to_addr}\n")
    if p.cc_addr:
        head += f"Cc: {p.cc_addr}\n"
    body = f"{(text or '').rstrip()}\n\n{head}\n{p.body}"
    return build(acc, to=to, cc=cc, bcc=bcc, subject=_subject("WG:", p.subject, keep_if=None), text=body,
                 attachments=(_original_attachments(msg) if with_attachments else []) + list(extra_attachments or []))


def prefill(acc: dict, raw: bytes, mode: str) -> dict:
    """Vorlage für das Schreibfenster: dieselben Regeln wie beim Senden (Empfänger, Präfix, Zitat/Kopf)."""
    msg, p = _orig(raw)
    if mode == "forward":
        head = ("---------- Weitergeleitete Nachricht ----------\n"
                f"Von: {p.from_addr}\nDatum: {p.date}\nBetreff: {p.subject}\nAn: {p.to_addr}\n")
        return {"to": "", "cc": "", "subject": _subject("WG:", p.subject, keep_if=None), "quote": f"{head}\n{p.body}",
                "attachments": [a.get("name", "") for a in p.attachments]}
    to, cc = _recipients(acc, msg, p, mode == "reply_all")
    return {"to": addresses.header(to), "cc": addresses.header(cc) if cc else "",
            "subject": _subject("Re:", p.subject, keep_if=_REPLY_PREFIX), "quote": _quote(p), "attachments": []}
