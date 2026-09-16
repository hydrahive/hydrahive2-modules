"""Walking-Skeleton-Verträge für Backend, Manifest und Frontend."""
from __future__ import annotations

import json
from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parents[1]


def test_status_requires_current_principal(client) -> None:
    response = client.get("/api/modules/telephony/status")

    assert response.status_code == 401


def test_status_is_honest_about_unavailable_telephony(client, auth_headers) -> None:
    response = client.get("/api/modules/telephony/status", headers=auth_headers)

    assert response.status_code == 200
    assert response.json() == {
        "module": "telephony",
        "stage": "foundation",
        "status": "not_configured",
        "configured": False,
        "telephony_available": False,
        "probe_target": {"registrar": "192.168.3.1", "port": 5060},
        "features": {
            "setup": False,
            "registration_probe": True,
            "incoming_call_probe": True,
            "inbound_calls": False,
            "outbound_calls": False,
            "archive": False,
        },
    }


def test_register_mounts_only_the_router() -> None:
    from backend import register, router

    class Context:
        def __init__(self) -> None:
            self.routers: list[object] = []

        def register_router(self, value: object) -> None:
            self.routers.append(value)

    ctx = Context()
    register(ctx)

    assert ctx.routers == [router]


def test_hub_publishes_telephony_module() -> None:
    hub = json.loads((MODULE_DIR.parent / "hub.json").read_text())

    assert {"id": "telephony", "name": "VoIP", "path": "telephony"} in hub["modules"]


def test_manifest_declares_installable_foundation() -> None:
    manifest = json.loads((MODULE_DIR / "manifest.json").read_text())

    assert manifest == {
        "id": "telephony",
        "name": "VoIP",
        "version": "0.4.0",
        "description": (
            "Projektgebundener Telefonassistent für VoIP-Zugänge, "
            "Telefonaufträge und Gesprächsarchive."
        ),
        "icon": "PhoneCall",
        "nav_group": "working",
        "permissions": [],
        "has_service": False,
        "default_agent_tools": False,
        "min_core_version": "2.0.0",
    }


def test_frontend_exports_confirmed_menu_contract() -> None:
    source = (MODULE_DIR / "frontend" / "index.tsx").read_text()

    assert 'path: "/voip"' in source
    assert 'labelKey: "voip"' in source
    assert 'icon: "PhoneCall"' in source
    assert 'group: "working"' in source
    assert "cockpit: true" in source
