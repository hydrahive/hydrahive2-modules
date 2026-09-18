from __future__ import annotations

from hydrahive.api.middleware.auth import create_token

BASE = "/api/modules/tickets"


def headers(username: str) -> dict[str, str]:
    users = {"member": "user-member", "other": "user-other"}
    return {"Authorization": f"Bearer {create_token(username, 'user', users[username])}"}


def test_notification_polling_is_user_scoped(client, ticket_db):
    created = client.post(
        f"{BASE}/tickets",
        json={"title": "Benachrichtigung", "assigned_to": "user-other"},
        headers=headers("member"),
    )
    own = client.get(f"{BASE}/notifications", headers=headers("member"))
    assigned = client.get(f"{BASE}/notifications", headers=headers("other"))

    assert created.status_code == 201
    assert own.json() == []
    assert len(assigned.json()) == 1
    notification_id = assigned.json()[0]["id"]
    marked = client.post(f"{BASE}/notifications/{notification_id}/read", headers=headers("other"))

    assert marked.json() == {"read": True}
    assert client.get(f"{BASE}/notifications", headers=headers("other")).json() == []
