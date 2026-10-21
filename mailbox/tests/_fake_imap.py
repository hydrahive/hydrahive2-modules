"""Fake-IMAP für die Abgleich-Tests: bildet genau die imaplib-Aufrufe nach, die backend/imap_conn.py nutzt.

Antworten im imaplib-Format (Typ, Daten-Liste). Ordner mit UIDVALIDITY, UIDs aufsteigend, Flags; Fehler einschleusbar.
"""
from __future__ import annotations

import imaplib
import re


class Box:
    def __init__(self, name, *, special="", uidvalidity=1000):
        self.name, self.special, self.uidvalidity = name, special, uidvalidity
        self.msgs: dict[int, tuple[bytes, set[str]]] = {}
        self.next_uid = 1

    def add(self, raw: bytes, flags=()):
        uid = self.next_uid
        self.msgs[uid] = (raw, set(flags))
        self.next_uid += 1
        return uid


class FakeServer:
    def __init__(self, user="till@example.net", password="pw"):
        self.user, self.password = user, password
        self.boxes: dict[str, Box] = {"INBOX": Box("INBOX")}
        self.fail_fetch_after: int | None = None   # nach so vielen FETCH-Aufrufen Verbindung „abbrechen“
        self.fetches = 0
        self.body_fetches = 0       # wie viele Mails mit Inhalt geladen wurden
        self.logins = 0
        self.writable_selects = 0   # SELECT ohne readonly (darf beim Abgleich nie vorkommen)
        self.appends: list = []     # (mailbox, flags, date_time, message)
        self.fail_append = False

    def box(self, name, **kw):
        self.boxes.setdefault(name, Box(name, **kw))
        return self.boxes[name]


def _set(spec: str) -> list[int]:
    out = []
    for part in spec.split(","):
        if ":" in part:
            a, b = part.split(":")
            out.append((int(a), None if b == "*" else int(b)))
        else:
            out.append((int(part), int(part)))
    return out


class FakeIMAP:
    def __init__(self, server: FakeServer):
        self.s = server
        self.selected: Box | None = None
        self.logged_in = False

    def login(self, user, password):
        self.s.logins += 1
        if (user, password) != (self.s.user, self.s.password):
            raise imaplib.IMAP4.error("[AUTHENTICATIONFAILED] Invalid credentials")
        self.logged_in = True
        return "OK", [b"LOGIN completed"]

    def list(self, directory='""', pattern="*"):
        lines = []
        for b in self.s.boxes.values():
            flags = "\\HasNoChildren" + (f" {b.special}" if b.special else "")
            name = b.name.encode("ascii") if b.name.isascii() else _utf7(b.name)
            lines.append(f"({flags}) \"/\" ".encode() + b'"' + name + b'"')
        return "OK", lines

    def select(self, mailbox, readonly=False):
        if not readonly:
            self.s.writable_selects += 1
        if not (mailbox.startswith('"') and mailbox.endswith('"')):
            return "BAD", [b"mailbox name must be quoted"]
        name = mailbox[1:-1].replace('\\"', '"').replace("\\\\", "\\")
        if re.search(r"&(?![A-Za-z0-9+,]*-)", name):
            return "BAD", [b"invalid modified UTF-7"]
        name = _from_utf7(name)
        if name not in self.s.boxes:
            return "NO", [b"Mailbox does not exist"]
        self.selected = self.s.boxes[name]
        return "OK", [str(len(self.selected.msgs)).encode()]

    def response(self, code):
        if code == "UIDVALIDITY" and self.selected:
            return code, [str(self.selected.uidvalidity).encode()]
        return code, [None]

    def uid(self, command, *args):
        b = self.selected
        cmd = command.upper()
        if b is None:
            return "BAD", [b"no mailbox selected"]
        if cmd == "SEARCH":
            return "OK", [" ".join(str(u) for u in sorted(b.msgs)).encode()]
        if cmd == "FETCH":
            self.s.fetches += 1
            if self.s.fail_fetch_after is not None and self.s.fetches > self.s.fail_fetch_after:
                raise imaplib.IMAP4.abort("socket error: EOF")
            spec, what = args[0], args[1].upper()
            uids = [u for u in sorted(b.msgs) if any(lo <= u and (hi is None or u <= hi) for lo, hi in _set(spec))]
            data = []
            for u in uids:
                raw, flags = b.msgs[u]
                fl = " ".join(sorted(flags))
                if "BODY.PEEK[]" in what:
                    self.s.body_fetches += 1
                    data.append((f"1 (UID {u} FLAGS ({fl}) BODY[] {{{len(raw)}}}".encode(), raw))
                    data.append(b")")
                elif "HEADER.FIELDS" in what:
                    m = re.search(rb"(?im)^message-id:.*\r?\n", raw)
                    hdr = (m.group(0) if m else b"") + b"\r\n"
                    data.append((f"1 (UID {u} FLAGS ({fl}) RFC822.SIZE {len(raw)} "
                                 f"BODY[HEADER.FIELDS (MESSAGE-ID)] {{{len(hdr)}}}".encode(), hdr))
                    data.append(b")")
                else:
                    data.append(f"1 (UID {u} FLAGS ({fl}))".encode())
            return "OK", data
        return "BAD", [b"unknown"]

    def append(self, mailbox, flags, date_time, message):
        """APPEND wie imaplib: Ordnername in Anführungszeichen, Flags „(\\Seen)“, Rohmail als bytes."""
        self.s.appends.append((mailbox, flags, date_time, message))
        if self.s.fail_append:
            return "NO", [b"[OVERQUOTA] mailbox full"]
        if not (mailbox.startswith('"') and mailbox.endswith('"')):
            return "BAD", [b"mailbox name must be quoted"]
        name = _from_utf7(mailbox[1:-1].replace('\\"', '"').replace("\\\\", "\\"))
        if name not in self.s.boxes:
            return "NO", [b"[TRYCREATE] Mailbox does not exist"]
        if b"\n" in message.replace(b"\r\n", b""):
            return "BAD", [b"bare newline"]
        uid = self.s.boxes[name].add(message, set((flags or "").strip("()").split()))
        return "OK", [f"[APPENDUID {self.s.boxes[name].uidvalidity} {uid}] APPEND completed".encode()]

    def logout(self):
        return "BYE", [b""]


def _utf7(s: str) -> bytes:
    import base64
    b = base64.b64encode(s.encode("utf-16-be")).rstrip(b"=").replace(b"/", b",")
    return b"&" + b + b"-"


def _from_utf7(s: str) -> str:
    import base64

    def dec(m):
        body = m.group(1).replace(",", "/")
        return base64.b64decode(body + "=" * (-len(body) % 4)).decode("utf-16-be") if body else "&"
    return re.sub(r"&([A-Za-z0-9+,]*)-", dec, s)
