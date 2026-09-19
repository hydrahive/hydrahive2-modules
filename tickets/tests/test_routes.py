from __future__ import annotations

from hydrahive.api.middleware.auth import create_token

BASE = "/api/modules/tickets/tickets"
OPERATIONS = "/api/modules/tickets"


def headers(username: str = "member") -> dict[str, str]:
    users = {"admin": "user-admin", "member": "user-member", "other": "user-other"}
    role = "admin" if username == "admin" else "user"
    return {"Authorization": f"Bearer {create_token(username, role, users[username])}"}


def test_ticket_routes_require_auth(client, ticket_db):
    assert client.get(BASE).status_code == 401


def test_create_detail_and_comments(client, ticket_db):
    response = client.post(BASE, json={"title": "Neuer interner Vorgang"}, headers=headers())
    assert response.status_code == 201
    ticket_id = response.json()["id"]

    comment = client.post(
        f"{BASE}/{ticket_id}/comments",
        json={"body": "Ich habe die Logs angehängt."},
        headers=headers(),
    )
    detail = client.get(f"{BASE}/{ticket_id}", headers=headers())

    assert comment.status_code == 201
    assert detail.status_code == 200
    assert detail.json()["comments"][0]["body"] == "Ich habe die Logs angehängt."
    assert detail.json()["events"][-1]["event_type"] == "comment_added"


def test_creator_can_update_but_other_user_cannot(client, ticket_db):
    created = client.post(BASE, json={"title": "Berechtigungen"}, headers=headers())
    ticket_id = created.json()["id"]

    denied = client.patch(
        f"{BASE}/{ticket_id}", json={"title": "Fremdänderung"}, headers=headers("other")
    )
    allowed = client.patch(
        f"{BASE}/{ticket_id}", json={"priority": "high"}, headers=headers()
    )

    assert denied.status_code == 403
    assert allowed.status_code == 200
    assert allowed.json()["priority"] == "high"


def test_filters_and_invalid_transition_have_stable_errors(client, ticket_db):
    created = client.post(BASE, json={"title": "Triage", "priority": "urgent"}, headers=headers())
    ticket_id = created.json()["id"]
    assert client.get(f"{BASE}?priority=urgent", headers=headers()).json()[0]["id"] == ticket_id

    assert client.patch(
        f"{BASE}/{ticket_id}", json={"status": "triaged"}, headers=headers()
    ).status_code == 200
    invalid = client.patch(
        f"{BASE}/{ticket_id}", json={"status": "closed"}, headers=headers()
    )
    assert invalid.status_code == 409
    assert invalid.json()["detail"]["code"] == "invalid_status_transition"


def test_unknown_ticket_is_not_leaked(client, ticket_db):
    response = client.get(f"{BASE}/does-not-exist", headers=headers())
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "ticket_not_found"


def test_operations_dashboard_and_saved_views(client, ticket_db):
    dashboard = client.get(f"{OPERATIONS}/dashboard", headers=headers())
    created = client.post(
        f"{OPERATIONS}/saved-views",
        json={"name": "Urgent", "filters": {"priority": "urgent"}, "sort": "due_at"},
        headers=headers(),
    )
    views = client.get(f"{OPERATIONS}/saved-views", headers=headers())

    assert dashboard.status_code == 200
    assert dashboard.json()["open"] == 0
    assert created.status_code == 201
    assert views.json()[0]["name"] == "Urgent"


def test_sla_profiles_are_admin_only(client, ticket_db):
    assert client.get(f"{OPERATIONS}/sla/profiles", headers=headers()).status_code == 403
    response = client.get(f"{OPERATIONS}/sla/profiles", headers=headers("admin"))

    assert response.status_code == 200
    assert response.json()[0]["id"] == "default"


def test_bulk_update_returns_per_ticket_results(client, ticket_db):
    own = client.post(BASE, json={"title": "Own"}, headers=headers())
    other = client.post(BASE, json={"title": "Other"}, headers=headers("other"))
    response = client.post(
        f"{OPERATIONS}/bulk-update",
        json={"ticket_ids": [own.json()["id"], other.json()["id"]], "update": {"priority": "high"}},
        headers=headers(),
    )

    assert response.status_code == 200
    assert response.json()["updated"] == 1
    assert response.json()["skipped"] == 1
