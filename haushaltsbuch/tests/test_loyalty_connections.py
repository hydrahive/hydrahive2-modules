from __future__ import annotations

from hydrahive.credentials.models import Credential

from conftest import PREFIX
from test_v1_api import _create_household


_CREATE = {
    "provider": "payback",
    "credential_ref": "payback-main",
    "provider_account_id": "real-card-number-123456",
    "masked_account": "****3456",
    "alias": "Meine PAYBACK Karte",
    "country_code": "DE",
    "language_code": "de",
    "visibility": "owner",
}
_SECRET = "super-secret-refresh-token"


def _credential(name: str = "payback-main") -> Credential:
    return Credential(name=name, type="bearer", value=_SECRET)


def _create_connection(client, headers, monkeypatch, **overrides):
    monkeypatch.setattr(
        "backend.loyalty_connections.get_credential",
        lambda username, name: _credential(name),
    )
    return client.post(
        f"{PREFIX}/loyalty/connections",
        headers=headers,
        json={**_CREATE, **overrides},
    )


def test_connection_requires_auth_and_household(client, owner_headers):
    assert client.get(f"{PREFIX}/loyalty/connections").status_code == 401
    response = client.get(f"{PREFIX}/loyalty/connections", headers=owner_headers)
    assert response.status_code == 404


def test_create_requires_existing_credential(client, owner_headers, monkeypatch):
    _create_household(client, owner_headers)
    monkeypatch.setattr(
        "backend.loyalty_connections.get_credential", lambda username, name: None
    )
    response = client.post(
        f"{PREFIX}/loyalty/connections", headers=owner_headers, json=_CREATE
    )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "credential_not_found"


def test_create_hashes_account_id_and_never_exposes_secret(
    client, owner_headers, monkeypatch
):
    _create_household(client, owner_headers)
    response = _create_connection(client, owner_headers, monkeypatch)
    assert response.status_code == 201, response.text
    connection = response.json()
    serialized = response.text
    assert "credential_ref" not in connection
    assert connection["masked_account"] == "****3456"
    assert "provider_account_id" not in connection
    assert _CREATE["provider_account_id"] not in serialized
    assert _SECRET not in serialized

    from hydrahive.db.connection import db

    with db() as conn:
        row = conn.execute(
            "SELECT * FROM module_haushaltsbuch_loyalty_connections WHERE id=?",
            (connection["id"],),
        ).fetchone()
    assert row["account_fingerprint"] != _CREATE["provider_account_id"]
    assert _CREATE["provider_account_id"] not in " ".join(map(str, row))
    assert _SECRET not in " ".join(map(str, row))


def test_duplicate_provider_account_is_rejected(client, owner_headers, monkeypatch):
    _create_household(client, owner_headers)
    first = _create_connection(client, owner_headers, monkeypatch)
    second = _create_connection(client, owner_headers, monkeypatch)
    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["detail"]["code"] == "loyalty_connection_exists"


def test_update_uses_revision_and_delete_is_household_scoped(
    client, owner_headers, outsider_headers, monkeypatch
):
    _create_household(client, owner_headers)
    connection = _create_connection(client, owner_headers, monkeypatch).json()

    hidden = client.put(
        f"{PREFIX}/loyalty/connections/{connection['id']}",
        headers=outsider_headers,
        json={"alias": "Fremd", "visibility": "household", "revision": 1},
    )
    assert hidden.status_code == 404

    updated = client.put(
        f"{PREFIX}/loyalty/connections/{connection['id']}",
        headers=owner_headers,
        json={"alias": "Familienkarte", "visibility": "household", "revision": 1},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["alias"] == "Familienkarte"
    assert updated.json()["revision"] == 2

    stale = client.put(
        f"{PREFIX}/loyalty/connections/{connection['id']}",
        headers=owner_headers,
        json={"alias": "Alt", "visibility": "owner", "revision": 1},
    )
    assert stale.status_code == 409

    deleted = client.delete(
        f"{PREFIX}/loyalty/connections/{connection['id']}?revision=2",
        headers=owner_headers,
    )
    assert deleted.status_code == 204
    assert client.get(
        f"{PREFIX}/loyalty/connections", headers=owner_headers
    ).json() == []


def test_connection_audit_contains_metadata_but_no_credentials(
    client, owner_headers, monkeypatch
):
    _create_household(client, owner_headers)
    _create_connection(client, owner_headers, monkeypatch)
    audit = client.get(f"{PREFIX}/audit", headers=owner_headers).text
    assert "loyalty_connection" in audit
    assert _SECRET not in audit
    assert _CREATE["provider_account_id"] not in audit
