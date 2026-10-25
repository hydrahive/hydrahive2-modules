"""Walking-Skeleton-Verträge für Backend, Manifest und Frontend."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

MODULE_DIR = Path(__file__).resolve().parents[1]


def test_status_requires_current_principal(client) -> None:
    response = client.get("/api/modules/telephony/status")

    assert response.status_code == 401


@pytest.mark.usefixtures("clean_rows")
def test_status_is_honest_about_unavailable_telephony(client, auth_headers) -> None:
    response = client.get("/api/modules/telephony/status", headers=auth_headers)

    assert response.status_code == 200
    assert response.json() == {
        "module": "telephony",
        "stage": "connection",
        "status": "not_configured",
        "configured": False,
        "telephony_available": False,
        "features": {
            "setup": True,
            "registration": True,
            "inbound_calls": True,
            "outbound_calls": False,
            "archive": False,
        },
    }


@pytest.mark.usefixtures("clean_rows")
def test_status_shows_own_connection(client, auth_headers) -> None:
    from unittest import mock

    from backend import connections
    from backend.conn_models import ConnectionIn
    with mock.patch.object(connections, "_resolve_target", lambda h: "192.168.178.1"):
        connections.save("user-owner", ConnectionIn(registrar="fritz.box", username="hydra-telefon",
                                                    password="Sehr-Geheim-42"))
    data = client.get("/api/modules/telephony/status", headers=auth_headers).json()
    assert data["configured"] is True and data["status"] == "disconnected"
    assert data["telephony_available"] is False


def test_register_mounts_router_migrations_and_job() -> None:
    from backend import register, router

    class Context:
        def __init__(self) -> None:
            self.routers: list[object] = []
            self.migrations: list[str] = []
            self.jobs: list[tuple] = []

        def register_router(self, value: object) -> None:
            self.routers.append(value)

        def register_migrations(self, rel: str) -> None:
            self.migrations.append(rel)

        def register_job(self, name, fn, interval_seconds, *, initial_delay_seconds=5.0) -> None:
            self.jobs.append((name, interval_seconds))

    ctx = Context()
    register(ctx)

    assert ctx.routers == [router]
    assert ctx.migrations == ["migrations"]
    assert ctx.jobs == [("connections", 60)]


def test_hub_publishes_telephony_module() -> None:
    hub = json.loads((MODULE_DIR.parent / "hub.json").read_text())

    assert {"id": "telephony", "name": "VoIP", "path": "telephony"} in hub["modules"]


def test_manifest_declares_installable_foundation() -> None:
    manifest = json.loads((MODULE_DIR / "manifest.json").read_text())

    assert manifest == {
        "id": "telephony",
        "name": "VoIP",
        "version": "0.8.0",
        "description": (
            "Telefonassistent für die FRITZ!Box und andere SIP-Anlagen – in Entwicklung. "
            "Verbindet HydraHive mit der Anlage und nimmt Anrufe mit einer Ansage oder dem KI-Telefon-Assistenten "
            "an (Anliegen aufnehmen, Fragen aus eigenem Wissenstext beantworten, Notiz). "
            "Selbst anrufen und Kontakte folgen."
        ),
        "icon": "PhoneCall",
        "nav_group": "working",
        "permissions": [],
        "has_service": False,
        "default_agent_tools": False,
        "min_core_version": "2.0.0",
        "capabilities": [
            {
                "id": "module.telephony",
                "label": "VoIP nutzen (Telefonanlage verbinden, später Anrufe)",
                "default": "admin_only",
            }
        ],
    }


def test_frontend_exports_confirmed_menu_contract() -> None:
    source = (MODULE_DIR / "frontend" / "index.tsx").read_text()

    assert 'path: "/voip"' in source
    assert 'labelKey: "voip"' in source
    assert 'icon: "PhoneCall"' in source
    assert 'group: "working"' in source
    assert "cockpit: true" in source
