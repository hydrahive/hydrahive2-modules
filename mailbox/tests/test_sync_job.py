"""M1 Schritt 10: Abgleich-Job – alle Konten, Fehler je Konto isoliert, kein Doppellauf, blockiert die Schleife nicht."""
from __future__ import annotations

import asyncio

import pytest
from _fake_imap import FakeIMAP, FakeServer

BASE = {"label": "P", "imap_host": "imap.example.net", "imap_port": 993, "imap_tls": "ssl",
        "smtp_host": "smtp.example.net", "smtp_port": 465, "smtp_tls": "ssl", "password": "pw"}


@pytest.fixture
def servers(monkeypatch, archive):
    from backend import accounts, sync_job
    monkeypatch.setattr(accounts, "_test_login", lambda acc, pw: {"folders": 1})
    srv = {}

    def opener(acc):
        s = srv[acc["address"]]
        if s == "down":
            raise OSError("Connection refused")
        return FakeIMAP(s)
    monkeypatch.setattr(sync_job, "_open", opener)
    return srv


def _acc(owner, addr, srv, server):
    from backend import accounts
    srv[addr] = server
    return accounts.create(owner, {**BASE, "address": addr, "username": addr})


def _mail(n):
    return f"From: a@x.de\r\nSubject: M{n}\r\nMessage-ID: <j{n}@x>\r\n\r\nx\r\n".encode()


def test_alle_konten_und_status(servers):
    from backend import accounts, sync_job
    s1, s2 = FakeServer(user="a@example.net"), FakeServer(user="b@example.net")
    s1.boxes["INBOX"].add(_mail(1))
    s2.boxes["INBOX"].add(_mail(2))
    a = _acc("alice", "a@example.net", servers, s1)
    b = _acc("bob", "b@example.net", servers, s2)
    asyncio.run(sync_job.job())
    assert accounts.get_own("alice", a["id"])["status"] == "ok"
    assert sync_job.progress(a["id"])["messages_done"] == 1 and sync_job.progress(b["id"])["messages_done"] == 1


def test_fehler_eines_kontos_stoppt_andere_nicht(servers):
    from backend import accounts, sync_job
    s2 = FakeServer(user="b@example.net")
    s2.boxes["INBOX"].add(_mail(2))
    a = _acc("alice", "a@example.net", servers, "down")
    b = _acc("alice", "b@example.net", servers, s2)
    asyncio.run(sync_job.job())
    assert accounts.get_own("alice", a["id"])["status"] == "error"
    assert "Connection refused" in accounts.get_own("alice", a["id"])["status_detail"]
    assert accounts.get_own("alice", b["id"])["status"] == "ok"


def test_falsches_passwort_wird_auth_failed(servers):
    from backend import accounts, sync_job
    s = FakeServer(user="a@example.net", password="anders")
    a = _acc("alice", "a@example.net", servers, s)
    asyncio.run(sync_job.job())
    assert accounts.get_own("alice", a["id"])["status"] == "auth_failed"


def test_kein_doppellauf(servers):
    from backend import sync_job
    s = FakeServer(user="a@example.net")
    a = _acc("alice", "a@example.net", servers, s)
    assert sync_job._claim(a["id"]) is True
    assert sync_job._claim(a["id"]) is False, "läuft schon"
    sync_job._release(a["id"], "")
    assert sync_job._claim(a["id"]) is True


def test_haengender_lauf_wird_nach_frist_freigegeben(servers, monkeypatch):
    """Nach einem Absturz mitten im Abgleich darf das Konto nicht ewig als „läuft“ gelten."""
    from backend import sync_job
    from hydrahive.db.connection import db
    s = FakeServer(user="a@example.net")
    a = _acc("alice", "a@example.net", servers, s)
    sync_job._claim(a["id"])
    with db() as c:
        c.execute("UPDATE module_mailbox_sync SET started_at='2000-01-01T00:00:00Z' WHERE account_id=?", (a["id"],))
    assert sync_job._claim(a["id"]) is True


def test_job_blockiert_die_schleife_nicht(servers, monkeypatch):
    """IMAP ist blockierend: es muss in einem Thread laufen, sonst steht das ganze HydraHive.
    Gemessen: Während der Abgleich 0,3 s schläft, muss ein anderer Task weiter ticken."""
    from backend import sync_job
    s = FakeServer(user="a@example.net")
    _acc("alice", "a@example.net", servers, s)
    import time
    real = sync_job._sync_one

    def slow(acc):
        time.sleep(0.3)
        return real(acc)
    monkeypatch.setattr(sync_job, "_sync_one", slow)

    async def main():
        ticks = []

        async def ticker():
            while True:
                ticks.append(time.monotonic())
                await asyncio.sleep(0.01)
        t = asyncio.create_task(ticker())
        await asyncio.sleep(0.02)            # Ticker läuft schon, bevor der Abgleich beginnt
        start = len(ticks)
        await sync_job.job()
        t.cancel()
        return len(ticks) - start
    assert asyncio.run(main()) >= 10, "Ereignisschleife stand still"


def test_jetzt_abrufen_nur_eigenes(servers):
    from backend import sync_job
    s = FakeServer(user="a@example.net")
    a = _acc("alice", "a@example.net", servers, s)
    assert asyncio.run(sync_job.sync_now("bob", a["id"])) is False
    assert asyncio.run(sync_job.sync_now("alice", a["id"])) is True


def test_passwort_nie_im_fehlertext_oder_log(servers, monkeypatch, caplog):
    """Manche Server/Bibliotheken schreiben die Login-Zeile in die Fehlermeldung – Passwort muss trotzdem raus."""
    import logging

    from backend import accounts, fetch, sync_job
    a = _acc("alice", "a@example.net", servers, FakeServer(user="a@example.net"))

    def leaky(acc):
        raise fetch.SyncError(f'LOGIN "a@example.net" "{accounts.password_of(acc["id"])}" failed')
    monkeypatch.setattr(sync_job, "_sync_one", leaky)
    with caplog.at_level(logging.WARNING):
        asyncio.run(sync_job.job())
    st = accounts.get_own("alice", a["id"])
    assert st["status"] == "error" and "LOGIN" in st["status_detail"], "Fehler bleibt lesbar"
    for where in (st["status_detail"], caplog.text, sync_job.progress(a["id"])["last_error"]):
        assert '"pw"' not in where and "***" in where, where
