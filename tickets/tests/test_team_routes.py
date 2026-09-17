from __future__ import annotations

from hydrahive.api.middleware.auth import create_token

BASE = "/api/modules/tickets"


def headers(username: str = "member") -> dict[str, str]:
    users = {"admin": "user-admin", "member": "user-member", "other": "user-other"}
    role = "admin" if username == "admin" else "user"
    return {"Authorization": f"Bearer {create_token(username, role, users[username])}"}


def test_only_admin_can_create_team(client, ticket_db):
    denied = client.post(f"{BASE}/teams", json={"name": "Ops"}, headers=headers())
    created = client.post(f"{BASE}/teams", json={"name": "Ops"}, headers=headers("admin"))

    assert denied.status_code == 403
    assert created.status_code == 201
    assert created.json()["name"] == "Ops"
    assert created.json()["members"] == []


def test_team_lead_can_update_and_manage_members(client, ticket_db):
    team = client.post(f"{BASE}/teams", json={"name": "Ops"}, headers=headers("admin")).json()
    team_id = team["id"]
    assert client.post(
        f"{BASE}/teams/{team_id}/members",
        json={"user_id": "user-member", "role": "lead"},
        headers=headers("admin"),
    ).status_code == 201

    updated = client.patch(
        f"{BASE}/teams/{team_id}", json={"description": "Bereitschaft"}, headers=headers()
    )
    added = client.post(
        f"{BASE}/teams/{team_id}/members",
        json={"user_id": "user-other", "role": "member"},
        headers=headers(),
    )
    removed = client.delete(
        f"{BASE}/teams/{team_id}/members/user-other", headers=headers()
    )

    assert updated.status_code == 200
    assert updated.json()["description"] == "Bereitschaft"
    assert added.status_code == 201
    assert removed.json() == {"removed": True}


def test_duplicate_team_and_unknown_user_return_codes(client, ticket_db):
    client.post(f"{BASE}/teams", json={"name": "Ops"}, headers=headers("admin"))
    duplicate = client.post(f"{BASE}/teams", json={"name": "Ops"}, headers=headers("admin"))
    team_id = client.get(f"{BASE}/teams", headers=headers()).json()[0]["id"]
    unknown = client.post(
        f"{BASE}/teams/{team_id}/members",
        json={"user_id": "missing"},
        headers=headers("admin"),
    )

    assert duplicate.status_code == 409
    assert duplicate.json()["detail"]["code"] == "team_name_taken"
    assert unknown.status_code == 404
    assert unknown.json()["detail"]["code"] == "user_not_found"
