"""Mail bauen (PLAN-M2 Schritt 2). Alle Kopfzeilen aus geprüften Werten (addresses.py), nie roh aus Eingaben.

Bcc kommt nur in den Umschlag (envelope), nie in die Mail. Text + maskiertes HTML, Signatur nach „-- “ (RFC 3676).
Antworten/Weiterleiten: reply.py.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from html import escape

from . import addresses

MAX_TOTAL = 25 * 1024 * 1024          # Anhänge gesamt (viele Server nehmen nicht mehr)
SUBJECT_MAX = 998
_BAD = re.compile(r"[\r\n\x00]")
_TYPE = re.compile(r"^[a-z0-9][a-z0-9!#$&^_.+-]{0,63}/[a-z0-9][a-z0-9!#$&^_.+-]{0,63}$")
_NAME_BAD = re.compile(r"[\x00-\x1f\x7f\"\\/]+")
_DANGEROUS_INLINE = {"text/html", "image/svg+xml", "application/xhtml+xml", "text/javascript"}


class ComposeError(ValueError):
    pass


@dataclass
class Built:
    raw: bytes
    envelope: list[str]        # alle Empfänger (To+Cc+Bcc) für den SMTP-Umschlag
    message_id: str


def _from(acc: dict) -> str:
    return addresses.header([addresses.Recipient(name=(acc.get("sender_name") or "").strip(), addr=acc["address"])])


def _text_with_signature(text: str, signature: str) -> str:
    body = (text or "").rstrip()
    if signature and signature.strip():
        body = f"{body}\n\n-- \n{signature.strip()}" if body else f"-- \n{signature.strip()}"
    return body + "\n"


def _html(text: str) -> str:
    return ('<html><body><div style="font-family:sans-serif;white-space:pre-wrap">'
            + escape(text) + "</div></body></html>")


def _clean_name(name: str) -> str:
    base = re.split(r"[\\/]", name or "")[-1]
    return _NAME_BAD.sub("_", base).strip(" .")[:200] or "anhang"


def _clean_type(ctype: str) -> tuple[str, str]:
    t = (ctype or "").strip().lower()
    if not _TYPE.match(t) or t in _DANGEROUS_INLINE:
        return "application", "octet-stream"
    return tuple(t.split("/", 1))  # type: ignore[return-value]


def assemble(acc: dict, *, to: list, cc: list, bcc: list, subject: str, text: str,
             attachments: list[tuple[str, str, bytes]] | None = None, extra_headers: dict | None = None) -> Built:
    if not (to or cc or bcc):
        raise ComposeError("mindestens ein Empfänger")
    if not isinstance(subject, str) or _BAD.search(subject) or len(subject) > SUBJECT_MAX:
        raise ComposeError("Betreff ungültig")
    total = sum(len(d) for _, _, d in attachments or [])
    if total > MAX_TOTAL:
        raise ComposeError(f"Anhänge zusammen höchstens {MAX_TOTAL // (1024 * 1024)} MB")
    m = EmailMessage()
    m["From"] = _from(acc)
    if to:
        m["To"] = addresses.header(to)
    if cc:
        m["Cc"] = addresses.header(cc)
    m["Subject"] = subject
    m["Date"] = formatdate(localtime=True)
    domain = acc["address"].rpartition("@")[2]
    mid = make_msgid(domain=domain)
    m["Message-ID"] = mid
    for k, v in (extra_headers or {}).items():
        if _BAD.search(v):
            raise ComposeError(f"{k} ungültig")
        m[k] = v
    body = _text_with_signature(text, acc.get("signature", ""))
    m.set_content(body)
    m.add_alternative(_html(body), subtype="html")
    for name, ctype, data in attachments or []:
        main, sub = _clean_type(ctype)
        m.add_attachment(data, maintype=main, subtype=sub, filename=_clean_name(name))
    envelope = []
    for r in [*to, *cc, *bcc]:
        if r.addr not in envelope:
            envelope.append(r.addr)
    return Built(raw=m.as_bytes(), envelope=envelope, message_id=mid)


def _parse(field: str, value: str) -> list:
    try:
        return addresses.parse_list(value or "")
    except addresses.AddressError as e:
        raise ComposeError(f"{field}: {e}") from None


def build(acc: dict, *, to: str = "", cc: str = "", bcc: str = "", subject: str, text: str,
          attachments: list[tuple[str, str, bytes]] | None = None, extra_headers: dict | None = None) -> Built:
    return assemble(acc, to=_parse("An", to), cc=_parse("Cc", cc), bcc=_parse("Bcc", bcc), subject=subject,
                    text=text, attachments=attachments, extra_headers=extra_headers)


from .reply import forward, reply  # noqa: E402,F401 - öffentliche API an einer Stelle
