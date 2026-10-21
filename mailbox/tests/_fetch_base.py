"""Gemeinsame Hilfen der Abgleich-Tests (Fake-IMAP-Server mit Ordnern, Zählen im Index)."""
from __future__ import annotations

import pytest
from _fake_imap import FakeIMAP, FakeServer
from conftest import eml

ACC = {"id": "acc1", "address": "till@example.net"}


def _mail(n: int, subject="Mail") -> bytes:
    return (f"From: a{n}@example.org\r\nSubject: {subject} {n}\r\nMessage-ID: <m{n}@example.org>\r\n"
            f"Date: Tue, 20 Oct 2026 09:{n % 60:02d}:00 +0000\r\n\r\nText {n}\r\n").encode()


@pytest.fixture
def server():
    s = FakeServer()
    s.box("Gesendet", special="\\Sent")
    s.box("Archiv/2019")
    s.box("Gelöschte Elemente", special="\\Trash")
    return s


def _sync(server, batch=200):
    from backend import fetch
    return fetch.sync_account(ACC, FakeIMAP(server), batch=batch)


def _count(where="1=1", args=()):
    from backend import index_db
    with index_db.connect() as c:
        return c.execute(f"SELECT count(*) FROM messages WHERE {where}", args).fetchone()[0]

