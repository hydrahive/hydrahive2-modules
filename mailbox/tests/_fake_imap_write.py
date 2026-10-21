"""Fake-IMAP mit Schreibbefehlen (M2 Schritt 7): STORE, MOVE, COPY, UID EXPUNGE, SEARCH HEADER, EXPUNGE.

Fähigkeiten (MOVE, UIDPLUS) einstellbar. Zählt pauschale EXPUNGE-Aufrufe (dürfen nie vorkommen) und prüft, dass
geschrieben wird nur nach SELECT ohne readonly.
"""
from __future__ import annotations

import re

from _fake_imap import FakeIMAP, _from_utf7


class FakeIMAPW(FakeIMAP):
    def __init__(self, server, caps=("MOVE", "UIDPLUS")):
        super().__init__(server)
        self.caps = tuple(caps)
        self.readonly = True
        server.__dict__.setdefault("full_expunges", 0)
        server.__dict__.setdefault("writes_readonly", 0)

    def capability(self):
        return "OK", [("IMAP4rev1 " + " ".join(self.caps)).encode()]

    def select(self, mailbox, readonly=False):
        self.readonly = readonly
        return super().select(mailbox, readonly=readonly)

    def _box(self, quoted: str):
        name = _from_utf7(quoted[1:-1].replace('\\"', '"').replace("\\\\", "\\")) if quoted.startswith('"') else None
        return self.s.boxes.get(name) if name else None

    def _write(self):
        if self.readonly:
            self.s.writes_readonly += 1

    def _uids(self, spec: str) -> list[int]:
        want = {int(x) for x in spec.split(",")}
        return [u for u in sorted(self.selected.msgs) if u in want]

    def uid(self, command, *args):
        cmd, b = command.upper(), self.selected
        if b is None:
            return "BAD", [b"no mailbox selected"]
        if cmd == "SEARCH" and args:
            m = re.fullmatch(r'HEADER Message-ID "(.+)"', " ".join(args))
            if not m:
                return "BAD", [b"unsupported search"]
            hits = [u for u, (raw, _) in b.msgs.items()
                    if re.search(rb"(?im)^message-id:\s*" + re.escape(m.group(1).encode()) + rb"\s*$", raw)]
            return "OK", [" ".join(map(str, sorted(hits))).encode()]
        if cmd == "STORE":
            self._write()
            spec, op, flags = args
            fl = set(flags.strip("()").split())
            for u in self._uids(spec):
                cur = b.msgs[u][1]
                cur |= fl if op.startswith("+") else set()
                cur -= fl if op.startswith("-") else set()
            return "OK", [b""]
        if cmd in ("MOVE", "COPY"):
            if cmd == "MOVE" and "MOVE" not in self.caps:
                return "BAD", [b"unknown command"]
            self._write() if cmd == "MOVE" else None
            dest = self._box(args[1])
            if dest is None:
                return "NO", [b"[TRYCREATE] no such mailbox"]
            for u in self._uids(args[0]):
                raw, fl = b.msgs[u]
                dest.add(raw, set(fl) - {"\\Deleted"})
                if cmd == "MOVE":
                    del b.msgs[u]
            return "OK", [b""]
        if cmd == "EXPUNGE":
            if "UIDPLUS" not in self.caps:
                return "BAD", [b"unknown command"]
            self._write()
            for u in self._uids(args[0]):
                if "\\Deleted" in b.msgs[u][1]:
                    del b.msgs[u]
            return "OK", [b""]
        return super().uid(command, *args)

    def expunge(self):
        self.s.full_expunges += 1
        for u in [u for u, (_, fl) in self.selected.msgs.items() if "\\Deleted" in fl]:
            del self.selected.msgs[u]
        return "OK", [b""]

    def close(self):
        """Wie RFC 3501 6.4.2: CLOSE entfernt still alle \\Deleted-Mails des Ordners (= pauschales EXPUNGE)."""
        if self.selected and not self.readonly:
            self.expunge()
        self.selected = None
        return "OK", [b""]

    def unselect(self):
        if "UNSELECT" not in self.caps:
            raise AssertionError("UNSELECT ohne Fähigkeit")
        self.selected = None
        return "OK", [b""]
