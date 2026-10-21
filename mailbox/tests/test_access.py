"""M1 Schritt 11: Besitz-Prüfung einzeln (erste Schicht vor der Suche, die selbst auch filtert)."""
from __future__ import annotations

import pytest
from conftest import eml

BASE = {"label": "P", "imap_host": "imap.example.net", "imap_port": 993, "imap_tls": "ssl", "smtp_host": "",
        "smtp_port": 465, "smtp_tls": "ssl", "password": "pw"}


@pytest.fixture
def two(archive, monkeypatch):
    from backend import accounts, parse, store
    monkeypatch.setattr(accounts, "_test_login", lambda acc, pw: {"folders": 1})
    a = accounts.create("alice", {**BASE, "address": "alice@example.net", "username": "alice@example.net"})
    b = accounts.create("bob", {**BASE, "address": "bob@example.net", "username": "bob@example.net"})
    fa, fb = store.folder(a["id"], "INBOX", role="inbox"), store.folder(b["id"], "INBOX", role="inbox")
    ma = store.add_message(a["id"], fa, 1, parse.parse(eml("plain")), path="a/1.eml", size=1, flags=set())
    mb = store.add_message(b["id"], fb, 1, parse.parse(eml("latin1")), path="b/1.eml", size=1, flags=set())
    return {"a": a, "b": b, "fa": fa, "fb": fb, "ma": ma, "mb": mb}


def test_mail_nur_eigene(two):
    from backend import access
    assert access.message_owned("alice", two["ma"])["account"] == "alice@example.net"
    assert access.message_owned("alice", two["mb"]) is None
    assert access.message_owned("carol", two["ma"]) is None, "ohne Konten nie etwas"
    assert access.message_owned("alice", 999999) is None


def test_ordner_nur_eigene(two):
    from backend import access
    accs = access.accounts_map("alice")
    assert access.folder_owned(accs, two["fa"]) is True
    assert access.folder_owned(accs, two["fb"]) is False
    assert access.folder_owned({}, two["fa"]) is False
    assert access.folder_owned(accs, 999999) is False


def test_ordnerliste_nur_eigene(two):
    from backend import access
    assert [f["id"] for f in access.folders_for("alice")] == [two["fa"]]
    assert access.folders_for("carol") == []
