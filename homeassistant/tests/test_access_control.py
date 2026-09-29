"""Schalten nur mit Freigabe homeassistant.control (Core: docs/specs/access-groups.md).

Läuft gegen beide Core-Stände:
  - mit Freigaben-System: Nutzer ohne Freigabe → 403, Admin → 200
  - ohne Freigaben-System: wie bisher, angemeldet reicht
"""
from __future__ import annotations

import pytest

from backend import access
from backend import client as ha_client

try:
    from hydrahive.access import capabilities
    from hydrahive.modules._manifest_caps import CapabilitySpec  # noqa: F401
    HAS_ACCESS = True
except ImportError:
    HAS_ACCESS = False


@pytest.fixture
def mock_call(monkeypatch):
    async def fake_call(domain, service, data):
        return []
    monkeypatch.setattr(ha_client, "call_service", fake_call)


@pytest.fixture
def declared(monkeypatch):
    """Katalog mit homeassistant.control wie aus dem echten Manifest."""
    import json
    from pathlib import Path

    from hydrahive.modules.manifest import ModuleManifest
    cat = capabilities.Catalog.with_core()
    cat.register_module(ModuleManifest.load(Path(__file__).resolve().parents[1] / "manifest.json"))
    monkeypatch.setattr(capabilities, "CATALOG", cat)
    assert json.loads((Path(__file__).resolve().parents[1] / "manifest.json").read_text())["capabilities"]
    return cat


def _headers(client, name):
    r = client.post("/api/auth/login", json={"username": name, "password": "testpass123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


_BODY = {"domain": "light", "service": "turn_on", "entity_id": "light.wohnzimmer"}


@pytest.mark.skipif(not HAS_ACCESS, reason="Core ohne Freigaben-System")
def test_manifest_maps_ha_call_service_to_control(declared):
    assert declared.capability_for_tool("ha_call_service", module_id="homeassistant") == access.CONTROL
    assert declared.get(access.CONTROL).default == "admin_only"
    assert declared.get("module.homeassistant").default == "everyone"


@pytest.mark.skipif(not HAS_ACCESS, reason="Core ohne Freigaben-System")
def test_user_without_grant_cannot_switch(client, declared, mock_call):
    r = client.post("/api/modules/homeassistant/service", json=_BODY, headers=_headers(client, "testuser"))
    assert r.status_code == 403


@pytest.mark.skipif(not HAS_ACCESS, reason="Core ohne Freigaben-System")
def test_admin_can_switch(client, declared, mock_call):
    r = client.post("/api/modules/homeassistant/service", json=_BODY, headers=_headers(client, "admin"))
    assert r.status_code == 200


@pytest.mark.skipif(HAS_ACCESS, reason="nur für Core ohne Freigaben-System")
def test_old_core_keeps_previous_behaviour(client, mock_call):
    r = client.post("/api/modules/homeassistant/service", json=_BODY, headers=_headers(client, "testuser"))
    assert r.status_code == 200
