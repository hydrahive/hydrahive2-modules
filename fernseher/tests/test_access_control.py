"""Schalten nur mit Freigabe fernseher.control (voreingestellt: nur Admin). Wie homeassistant/tests."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from backend import access
from conftest import login

try:
    from hydrahive.access import capabilities
    from hydrahive.modules._manifest_caps import CapabilitySpec  # noqa: F401
    HAS_ACCESS = True
except ImportError:
    HAS_ACCESS = False

MANIFEST = Path(__file__).resolve().parents[1] / "manifest.json"
P = "/api/modules/fernseher"
SWITCH = [("channel", {"sender": "ZDF"}), ("volume", {"wert": "+1"}), ("mute", {"stumm": True}),
          ("power", {"an": True}), ("app", {"name": "Plex"})]


@pytest.fixture
def declared(monkeypatch):
    from hydrahive.modules.manifest import ModuleManifest
    cat = capabilities.Catalog.with_core()
    cat.register_module(ModuleManifest.load(MANIFEST))
    monkeypatch.setattr(capabilities, "CATALOG", cat)
    return cat


def test_manifest():
    m = json.loads(MANIFEST.read_text())
    assert m["id"] == "fernseher" and m["has_service"] is False
    caps = {c["id"]: c for c in m["capabilities"]}
    assert caps["module.fernseher"]["default"] == "everyone"
    assert caps[access.CONTROL]["default"] == "admin_only"
    assert sorted(caps[access.CONTROL]["tools"]) == ["tv_app", "tv_lautstaerke", "tv_power", "tv_sender"]


@pytest.mark.skipif(not HAS_ACCESS, reason="Core ohne Freigaben-System")
def test_schaltende_werkzeuge_brauchen_control(declared):
    for t in ["tv_sender", "tv_lautstaerke", "tv_power", "tv_app"]:
        assert declared.capability_for_tool(t, module_id="fernseher") == access.CONTROL
    for t in ["tv_status", "tv_sender_liste"]:
        assert declared.capability_for_tool(t, module_id="fernseher") == "module.fernseher"


@pytest.mark.skipif(not HAS_ACCESS, reason="Core ohne Freigaben-System")
@pytest.mark.parametrize(("path", "body"), SWITCH)
def test_nutzer_ohne_freigabe_darf_nicht_schalten(client, configured, declared, path, body):
    before = (configured.playing, configured.volume, configured.mute, configured.power)
    r = client.post(f"{P}/{path}", json=body, headers=login(client, "testuser"))
    assert r.status_code == 403
    assert (configured.playing, configured.volume, configured.mute, configured.power) == before
    assert not any(c[1].startswith("set") for c in configured.calls)


@pytest.mark.skipif(not HAS_ACCESS, reason="Core ohne Freigaben-System")
@pytest.mark.parametrize(("path", "body"), SWITCH)
def test_admin_darf_schalten(client, configured, declared, path, body):
    assert client.post(f"{P}/{path}", json=body, headers=login(client, "admin")).status_code == 200
