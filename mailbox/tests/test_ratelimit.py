"""M2 Schritt 4: Versandgrenze je Konto (Spec §11: 20 je Stunde, einstellbar), gezählt ohne Inhalt."""
from __future__ import annotations

import pytest


def test_grenze_je_konto(monkeypatch):
    from backend import ratelimit
    t = [1000.0]
    monkeypatch.setattr(ratelimit.time, "time", lambda: t[0])
    for _ in range(20):
        ratelimit.check("acc1")
        ratelimit.record("acc1", recipients=2)
    with pytest.raises(ratelimit.RateLimited) as e:
        ratelimit.check("acc1")
    assert 3590 <= e.value.retry_after <= 3600
    ratelimit.check("acc2")                       # anderes Konto unberührt


def test_fenster_gleitet(monkeypatch):
    from backend import ratelimit
    t = [1000.0]
    monkeypatch.setattr(ratelimit.time, "time", lambda: t[0])
    for i in range(20):
        t[0] = 1000.0 + i * 60
        ratelimit.record("acc1", recipients=1)
    t[0] = 1000.0 + 3599
    with pytest.raises(ratelimit.RateLimited) as e:
        ratelimit.check("acc1")
    assert e.value.retry_after == 1
    t[0] = 1000.0 + 3600.5                        # die erste ist aus dem Fenster
    ratelimit.check("acc1")


def test_einstellbar(monkeypatch):
    from backend import ratelimit
    monkeypatch.setenv("HH_MAILBOX_SEND_PER_HOUR", "2")
    ratelimit.record("acc1", recipients=1)
    ratelimit.record("acc1", recipients=1)
    with pytest.raises(ratelimit.RateLimited):
        ratelimit.check("acc1")


@pytest.mark.parametrize("bad", ["", "abc", "0", "-5", "100000"])
def test_ungueltige_einstellung_faellt_auf_standard(monkeypatch, bad):
    from backend import ratelimit
    monkeypatch.setenv("HH_MAILBOX_SEND_PER_HOUR", bad)
    assert ratelimit.limit() == 20


def test_zaehlt_ohne_inhalt():
    from backend import ratelimit
    from hydrahive.db.connection import db
    ratelimit.record("acc1", recipients=3)
    with db() as c:
        cols = [r[1] for r in c.execute("PRAGMA table_info(module_mailbox_sendlog)")]
        row = c.execute("SELECT account_id, recipients FROM module_mailbox_sendlog").fetchone()
    assert set(cols) == {"id", "account_id", "sent_at", "recipients"} and tuple(row) == ("acc1", 3)


def test_alte_eintraege_werden_aufgeraeumt(monkeypatch):
    from backend import ratelimit
    from hydrahive.db.connection import db
    t = [1000.0]
    monkeypatch.setattr(ratelimit.time, "time", lambda: t[0])
    ratelimit.record("acc1", recipients=1)
    t[0] = 1000.0 + 2 * 86400
    ratelimit.record("acc1", recipients=1)
    with db() as c:
        assert c.execute("SELECT COUNT(*) FROM module_mailbox_sendlog").fetchone()[0] == 1
