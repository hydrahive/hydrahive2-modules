from __future__ import annotations

BASE = "/api/modules/game-studio"


def test_module_registration_uses_root_migrations() -> None:
    from backend import register

    class Context:
        def __init__(self):
            self.routers = []
            self.migrations = []

        def register_router(self, router):
            self.routers.append(router)

        def register_migrations(self, path: str):
            self.migrations.append(path)

    context = Context()
    register(context)
    assert len(context.routers) == 1
    assert context.migrations == ["migrations"]


def _login(client, username: str) -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": "testpass123"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _draft(title: str = "Leuchtturm im Sturm") -> dict:
    return {
        "entry_kind": "new",
        "title": title,
        "idea": "Der Spieler hält ein Leuchtfeuer während eines Sturms am Leben.",
        "genre": "Puzzle-Abenteuer",
        "target_platform": "desktop",
    }


def test_routes_require_authentication(client) -> None:
    assert client.get(f"{BASE}/overview").status_code in (401, 403)
    assert client.post(f"{BASE}/drafts", json=_draft()).status_code in (401, 403)


def test_overview_is_honest_and_starts_without_demo_projects(client, auth_headers) -> None:
    response = client.get(f"{BASE}/overview", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["drafts"] == []
    assert body["workstation"]["code"] in {"core_update_required", "not_connected"}
    assert body["workstation"]["build_available"] is False
    assert body["runner"] == {"code": "runner_pending_pr4", "build_available": False}


def test_draft_survives_steps_and_uses_optimistic_revision(client, auth_headers) -> None:
    created_response = client.post(f"{BASE}/drafts", headers=auth_headers, json=_draft())
    assert created_response.status_code == 201, created_response.text
    created = created_response.json()
    assert created["revision"] == 1
    assert created["current_step"] == 1

    skipped = client.patch(
        f"{BASE}/drafts/{created['draft_id']}",
        headers=auth_headers,
        json={"revision": 1, "current_step": 4},
    )
    assert skipped.status_code == 400
    assert client.patch(
        f"{BASE}/drafts/{created['draft_id']}",
        headers=auth_headers,
        json={"revision": 1, "current_step": 5},
    ).status_code == 422

    updated_response = client.patch(
        f"{BASE}/drafts/{created['draft_id']}",
        headers=auth_headers,
        json={
            "revision": created["revision"],
            "core_action": "Brennstoff verteilen und das Licht ausrichten.",
            "success_condition": "Das Schiff erreicht sichtbar den sicheren Hafen.",
            "current_step": 4,
        },
    )
    assert updated_response.status_code == 200, updated_response.text
    updated = updated_response.json()
    assert updated["revision"] == 2
    assert updated["current_step"] == 4

    conflict = client.patch(
        f"{BASE}/drafts/{created['draft_id']}",
        headers=auth_headers,
        json={"revision": 1, "title": "Veraltete Änderung"},
    )
    assert conflict.status_code == 409

    overview = client.get(f"{BASE}/overview", headers=auth_headers).json()
    assert [draft["draft_id"] for draft in overview["drafts"]] == [created["draft_id"]]
    assert overview["drafts"][0]["core_action"].startswith("Brennstoff")


def test_drafts_are_isolated_by_immutable_user(client) -> None:
    owner = _login(client, "testuser")
    other = _login(client, "other")
    draft_id = client.post(f"{BASE}/drafts", headers=owner, json=_draft("Privater Entwurf")).json()["draft_id"]

    assert client.get(f"{BASE}/overview", headers=other).json()["drafts"] == []
    assert client.get(f"{BASE}/drafts/{draft_id}", headers=other).status_code == 404
    assert client.patch(
        f"{BASE}/drafts/{draft_id}", headers=other, json={"revision": 1, "title": "Fremd"}
    ).status_code == 404


def test_request_schemas_reject_unknown_fields_and_blank_title(client, auth_headers) -> None:
    unknown = _draft()
    unknown["shell"] = "godot --editor"
    assert client.post(f"{BASE}/drafts", headers=auth_headers, json=unknown).status_code == 422

    blank = _draft("   ")
    assert client.post(f"{BASE}/drafts", headers=auth_headers, json=blank).status_code == 422
