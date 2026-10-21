"""M2: Admin-Freigabe für Mailserver im Heimnetz (Spec §11: keine internen Adressen ohne Admin-Freigabe).

Einstellung HH_MAILBOX_ALLOW_INTERNAL in /etc/hydrahive2/env (nur der Admin kann sie ändern): Hostnamen oder IPs,
durch Komma getrennt. Keine Muster, keine Netzbereiche – genau die genannten Namen.
"""
from __future__ import annotations

import pytest


def test_ohne_einstellung_leer(monkeypatch):
    from backend import accounts
    monkeypatch.delenv("HH_MAILBOX_ALLOW_INTERNAL", raising=False)
    assert accounts.allowed_internal_hosts() == set()


def test_namen_bereinigt(monkeypatch):
    from backend import accounts
    monkeypatch.setenv("HH_MAILBOX_ALLOW_INTERNAL", " Mail.Heim.Lan. , 192.168.178.50,,")
    assert accounts.allowed_internal_hosts() == {"mail.heim.lan", "192.168.178.50"}


@pytest.mark.parametrize("bad", ["*", "*.lan", "192.168.0.0/16", "mail lan", "a" * 254, "http://x", "x;y"])
def test_muster_und_unsinn_ignoriert(monkeypatch, bad):
    from backend import accounts
    monkeypatch.setenv("HH_MAILBOX_ALLOW_INTERNAL", f"{bad},ok.lan")
    assert accounts.allowed_internal_hosts() == {"ok.lan"}


def test_freigabe_wirkt_nur_fuer_genau_diesen_namen(monkeypatch):
    from backend import accounts, netcheck
    monkeypatch.setenv("HH_MAILBOX_ALLOW_INTERNAL", "mail.heim.lan")
    allow = accounts.allowed_internal_hosts()
    assert netcheck.check("mail.heim.lan", 993, resolve=lambda h: ["192.168.178.50"], allow_internal=allow) == "192.168.178.50"
    with pytest.raises(netcheck.HostBlocked):
        netcheck.check("andere.heim.lan", 993, resolve=lambda h: ["192.168.178.50"], allow_internal=allow)
