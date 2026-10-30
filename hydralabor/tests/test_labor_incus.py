"""Lesen der incus-Listen: Namen aus der ersten Spalte (incus 6.0.0 kennt bei network/acl/snapshot kein -c)."""
from __future__ import annotations

import asyncio

from backend import incus, network, provision


def test_erste_spalte():
    out = 'frisch,2026/10/30 14:35 UTC," ",NO\nhhlabor-acl,,1\n\n  \nhhlabor0,bridge,YES,10.77.0.1/24\n'
    assert incus.first_column(out) == {"frisch", "hhlabor-acl", "hhlabor0"}


def test_leere_ausgabe():
    assert incus.first_column("") == set()
    assert incus.first_column("\n \n") == set()


def test_listenfehler_mit_namen_in_ausgabe_zaehlt_nicht(fake_incus, monkeypatch):
    """rc != 0 → nichts gilt als vorhanden, auch wenn der Name zufällig in der Ausgabe steht."""
    async def failing(*a, **k):
        return 1, "frisch,x\nhhlabor0,x\nhhlabor-acl,x\n", "boom"
    monkeypatch.setattr(incus, "run", failing)
    assert asyncio.run(provision.has_snapshot()) is False
    assert asyncio.run(network._names("network")) == set()
