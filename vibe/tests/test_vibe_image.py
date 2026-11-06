"""Baustein 5: Das Container-Image ist fest gepinnt, nicht die Ubuntu-Version des Servers (PLAN-V1.md, Änderung 5.11.).

Befund der echten Probe auf .4 (Ubuntu 26.04, incus 6.0.0): Ein Container aus `images:ubuntu/26.04` bekommt NIE eine
IPv4-Adresse (systemd bleibt bei „initializing“), auch nicht am Standardnetz ohne Sperrregeln – es liegt am Image, nicht
an Vibe. `images:ubuntu/24.04` bekommt seine Adresse nach 1 s. Würde Vibe die Server-Version übernehmen (wie das Labor),
bekäme auf einem 26.04-Server jedes Projekt ein Image, das nicht startet. Darum: festes, getestetes Image.
"""
from __future__ import annotations

import asyncio

import pytest
from backend import container, network


def run(coro):
    return asyncio.run(coro)


@pytest.fixture
def net(fake_incus, monkeypatch):
    monkeypatch.setattr(network, "_host_networks", lambda: set())
    monkeypatch.setattr(network, "_host_addresses", lambda: set())
    run(network.ensure_network())
    return fake_incus


def test_image_ist_fest_24_04():
    assert container.IMAGE_RELEASE == "24.04"


def test_launch_nutzt_das_feste_image(net):
    run(container.launch("p1", container.Limits()))
    a = next(c for c in net.calls if c[0] == "launch")
    assert a[-2:] == ["images:ubuntu/24.04", "hh-vibe-p1"] and a[-3] == "--"


@pytest.mark.parametrize("os_release", ['VERSION_ID="26.04"\nID=ubuntu\n', 'VERSION_ID="22.04"\nID=ubuntu\n',
                                        'VERSION_ID="12"\nID=debian\n', ""])
def test_server_version_aendert_das_image_nicht(net, monkeypatch, tmp_path, os_release):
    """Egal, welches System der Server hat: das Image bleibt 24.04."""
    f = tmp_path / "os-release"
    f.write_text(os_release)
    import pathlib
    real = pathlib.Path.read_text

    def fake(self, *a, **k):
        return real(f, *a, **k) if str(self) == "/etc/os-release" else real(self, *a, **k)
    monkeypatch.setattr(pathlib.Path, "read_text", fake)
    run(container.launch("p1", container.Limits()))
    assert next(c for c in net.calls if c[0] == "launch")[-2] == "images:ubuntu/24.04"


def test_kein_lesen_der_server_version_mehr():
    assert not hasattr(container, "_ubuntu_version")
