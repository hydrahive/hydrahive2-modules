"""Löschen von Gesundheitsdaten: HTTP-Ebene (Auth, Bestätigung, Fehlercodes)."""
from __future__ import annotations

from hydrahive.db._utils import uuid7
from hydrahive.db.connection import db

BASE = "/api/modules/patientenakte/data-deletion"


def _fhir(user: str) -> None:
    with db() as conn:
        conn.execute(
            "INSERT INTO fhir_resources (id, user_id, resource_type, resource_id, resource_json) "
            "VALUES (?, ?, 'Condition', ?, '{}')", (uuid7(), user, uuid7()))


def _fhir_count(user: str) -> int:
    with db() as conn:
        return conn.execute("SELECT COUNT(*) FROM fhir_resources WHERE user_id = ?", (user,)).fetchone()[0]


def test_requires_login(client):
    assert client.post(BASE, json={"scope": "fhir", "confirm": "LÖSCHEN"}).status_code == 401
    assert client.get(f"{BASE}/overview").status_code == 401


def test_wrong_confirmation_deletes_nothing(client, auth_headers):
    _fhir("testuser")
    for confirm in (None, "", "löschen", "JA"):
        body = {"scope": "fhir"} if confirm is None else {"scope": "fhir", "confirm": confirm}
        r = client.post(BASE, json=body, headers=auth_headers)
        assert r.status_code == 400, confirm
        assert r.json()["detail"] == "confirmation_required"
    assert _fhir_count("testuser") == 1


def test_deletes_only_caller_data(client, auth_headers):
    _fhir("testuser")
    _fhir("admin")
    r = client.post(BASE, json={"scope": "fhir", "confirm": "LÖSCHEN"}, headers=auth_headers)
    assert r.status_code == 200, r.text
    assert r.json()["deleted"] == {"fhir_resources": 1}
    assert _fhir_count("testuser") == 0
    assert _fhir_count("admin") == 1


def test_user_id_in_body_is_ignored(client, auth_headers):
    """Man kann nicht fremde Daten löschen, indem man einen User mitschickt."""
    _fhir("admin")
    r = client.post(BASE, json={"scope": "fhir", "confirm": "LÖSCHEN", "user_id": "admin"},
                    headers=auth_headers)
    assert r.status_code == 200
    assert _fhir_count("admin") == 1


def test_stale_token_of_recreated_user_is_rejected(client, auth_headers):
    """Token eines gelöschten und neu angelegten Users darf nichts löschen."""
    import json

    from hydrahive.settings import settings

    users_file = settings.config_dir / "users.json"
    original = users_file.read_text()
    users = json.loads(original)
    users["testuser"]["user_id"] = "neu-angelegt-" + users["testuser"].get("user_id", "x")
    users_file.write_text(json.dumps(users))
    try:
        _fhir("testuser")
        r = client.post(BASE, json={"scope": "fhir", "confirm": "LÖSCHEN"}, headers=auth_headers)
        assert r.status_code == 401
        assert _fhir_count("testuser") == 1
    finally:
        users_file.write_text(original)


def test_invalid_scope_or_range_is_422(client, auth_headers):
    for body in (
        {"scope": "alles", "confirm": "LÖSCHEN"},
        {"scope": "fhir", "confirm": "LÖSCHEN", "from": "2025-01-01", "to": "2025-02-01"},
        {"scope": "apple_health", "confirm": "LÖSCHEN", "from": "2025-02-01", "to": "2025-01-01"},
        {"scope": "apple_health", "confirm": "LÖSCHEN", "from": "2025-01-01"},
    ):
        assert client.post(BASE, json=body, headers=auth_headers).status_code == 422, body


def test_overview(client, auth_headers):
    _fhir("testuser")
    r = client.get(f"{BASE}/overview", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["fhir"] == 1
    assert body["apple_health"]["raw"] == 0
    assert body["akte"] is False


def test_no_agent_tool_can_delete():
    """Die Agent-Tools bleiben rein lesend (Spec: Löschen nur durch den User)."""
    import backend

    class Ctx:
        def __init__(self):
            self.tools = []

        def register_router(self, _r):
            pass

        def register_migrations(self, _m):
            pass

        def register_tool(self, tool):
            self.tools.append(tool)

    ctx = Ctx()
    backend.register(ctx)
    names = {t.name for t in ctx.tools}
    assert names == {"query_fhir_data", "query_health_data"}
