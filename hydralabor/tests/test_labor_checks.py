"""Hydra-Labor L1 Schritt 4a: Voraussetzungen (Assistent Schritt 1). Jede Prüfung einzeln, mit klarem Grund."""
from __future__ import annotations

import asyncio

import pytest
from backend import checks


def run(coro):
    return asyncio.run(coro)


@pytest.fixture
def ok(fake_incus, monkeypatch):
    fake_incus.exec_answers = {}
    monkeypatch.setattr(checks, "_mem_available_mb", lambda: 12000)
    monkeypatch.setattr(checks, "_core_has_k1", lambda: True)
    monkeypatch.setattr(checks, "_incus_version", lambda: _v("6.0.5"))
    monkeypatch.setattr(checks, "_pool_free_gb", lambda: _v(500))
    return fake_incus


def _v(x):
    async def f():
        return x
    return f()


def ids(res):
    return {c["id"]: c["ok"] for c in res["checks"]}


def test_alles_gruen(ok):
    res = run(checks.run(disk_gb=20, ram_mb=4096))
    assert res["ok"] is True
    assert ids(res) == {"incus": True, "incus_version": True, "storage": True, "memory": True, "core": True}


def test_incus_fehlt(ok, monkeypatch):
    from backend import incus
    monkeypatch.setattr(incus, "available", lambda: False)
    res = run(checks.run(disk_gb=20, ram_mb=4096))
    assert res["ok"] is False and ids(res)["incus"] is False
    assert next(c for c in res["checks"] if c["id"] == "incus")["code"] == "labor_incus_missing"


@pytest.mark.parametrize(("ver", "good"), [("6.0.0", True), ("6.0.5", True), ("6.12", True), ("5.21.2", False),
                                          ("", False), ("kaputt", False)])
def test_incus_version(ok, monkeypatch, ver, good):
    monkeypatch.setattr(checks, "_incus_version", lambda: _v(ver))
    assert ids(run(checks.run(disk_gb=20, ram_mb=4096)))["incus_version"] is good


@pytest.mark.parametrize(("free", "good"), [(30, True), (29, False), (None, False)])
def test_platz_mit_puffer(ok, monkeypatch, free, good):
    """Platz für den Container + 10 GB Puffer (Bild, Sicherungspunkt)."""
    monkeypatch.setattr(checks, "_pool_free_gb", lambda: _v(free))
    res = run(checks.run(disk_gb=20, ram_mb=4096))
    assert ids(res)["storage"] is good and res["ok"] is good


@pytest.mark.parametrize(("mem", "good"), [(4096, True), (4095, False), (None, False)])
def test_arbeitsspeicher(ok, monkeypatch, mem, good):
    monkeypatch.setattr(checks, "_mem_available_mb", lambda: mem)
    assert ids(run(checks.run(disk_gb=20, ram_mb=4096)))["memory"] is good


def test_kern_ohne_k1(ok, monkeypatch):
    monkeypatch.setattr(checks, "_core_has_k1", lambda: False)
    res = run(checks.run(disk_gb=20, ram_mb=4096))
    assert ids(res)["core"] is False
    assert next(c for c in res["checks"] if c["id"] == "core")["code"] == "labor_core_too_old"


def test_meminfo_lesen(tmp_path):
    f = tmp_path / "meminfo"
    f.write_text("MemTotal:       16000000 kB\nMemAvailable:    8192000 kB\n")
    assert checks._mem_available_mb(f) == 8000
    f.write_text("kaputt\n")
    assert checks._mem_available_mb(f) is None
    assert checks._mem_available_mb(tmp_path / "fehlt") is None


def test_k1_im_kern_vorhanden():
    assert checks._core_has_k1() is True                    # Testumgebung = Kern mit K1 (bf9f02b8)


def test_version_und_platz_aus_incus(fake_incus):
    fake_incus.exec_answers = {}
    fake_incus.version = "Client version: 6.0.0\nServer version: 6.0.0\n"
    fake_incus.storage_info = '  space used: "221422673920"\n  total space: "2000397864960"\n'
    assert run(checks._incus_version()) == "6.0.0"
    assert run(checks._pool_free_gb()) == 1656


def test_version_fehler_von_incus(fake_incus, monkeypatch):
    from backend import incus

    async def failing(*a, **k):
        return 1, "Server version: 6.0.5\n", "boom"
    monkeypatch.setattr(incus, "run", failing)
    assert run(checks._incus_version()) == ""
    assert run(checks._pool_free_gb()) is None
