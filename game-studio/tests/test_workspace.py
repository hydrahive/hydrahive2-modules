from __future__ import annotations

from hydrahive.projects._paths import workspace_path

BASE = "/api/modules/game-studio"


def _login(client, username: str) -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": "testpass123"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _create(client, headers, title: str = "Arbeitsflaeche") -> str:
    response = client.post(f"{BASE}/projects", headers=headers, json={
        "entry_kind": "new", "engine": "unreal", "engine_version": "auto", "title": title,
        "idea": "Ein Testspiel.", "genre": "Abenteuer", "target_platform": "desktop",
    })
    assert response.status_code == 201, response.text
    return response.json()["project_id"]


def test_starter_documents_are_files_in_workspace(client, admin_headers) -> None:
    project_id = _create(client, admin_headers)
    response = client.get(f"{BASE}/projects/{project_id}/design", headers=admin_headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["can_write"] is True
    assert [doc["slug"] for doc in body["docs"]] == ["spielidee", "mechaniken", "figuren", "welt-und-story", "level"]
    design = workspace_path(project_id) / "game-studio" / "design"
    assert (design / "spielidee.md").read_text().startswith("# Spielidee")


def test_starters_never_overwrite_existing_files(client, admin_headers) -> None:
    project_id = _create(client, admin_headers, "Vorhanden")
    design = workspace_path(project_id) / "game-studio" / "design"
    design.mkdir(parents=True)
    (design / "spielidee.md").write_text("# Meine Idee\n\nSchon geschrieben.\n")
    client.get(f"{BASE}/projects/{project_id}/design", headers=admin_headers)
    assert (design / "spielidee.md").read_text() == "# Meine Idee\n\nSchon geschrieben.\n"


def test_save_uses_etag_and_rejects_stale_writes(client, admin_headers) -> None:
    project_id = _create(client, admin_headers, "Sperre")
    client.get(f"{BASE}/projects/{project_id}/design", headers=admin_headers)
    doc = client.get(f"{BASE}/projects/{project_id}/design/mechaniken", headers=admin_headers).json()

    saved = client.put(f"{BASE}/projects/{project_id}/design/mechaniken", headers=admin_headers,
                       json={"content": "# Mechaniken\n\nSpringen.\n", "etag": doc["etag"]})
    assert saved.status_code == 200, saved.text
    assert saved.json()["etag"] != doc["etag"]

    stale = client.put(f"{BASE}/projects/{project_id}/design/mechaniken", headers=admin_headers,
                       json={"content": "# Mechaniken\n\nAlt.\n", "etag": doc["etag"]})
    assert stale.status_code == 409
    path = workspace_path(project_id) / "game-studio" / "design" / "mechaniken.md"
    assert path.read_text() == "# Mechaniken\n\nSpringen.\n"


def test_create_custom_document_and_reject_duplicates(client, admin_headers) -> None:
    project_id = _create(client, admin_headers, "Eigene")
    created = client.post(f"{BASE}/projects/{project_id}/design", headers=admin_headers, json={"title": "Gegner & Bosse"})
    assert created.status_code == 201, created.text
    assert created.json()["slug"] == "gegner-bosse"
    assert created.json()["title"] == "Gegner & Bosse"
    again = client.post(f"{BASE}/projects/{project_id}/design", headers=admin_headers, json={"title": "Gegner & Bosse"})
    assert again.status_code == 409


def test_paths_symlinks_and_size_are_rejected(client, admin_headers, tmp_path) -> None:
    project_id = _create(client, admin_headers, "Sicherheit")
    client.get(f"{BASE}/projects/{project_id}/design", headers=admin_headers)
    assert client.get(f"{BASE}/projects/{project_id}/design/..%2Fproject", headers=admin_headers).status_code in (400, 404)
    assert client.put(f"{BASE}/projects/{project_id}/design/BAD_SLUG", headers=admin_headers,
                      json={"content": "x", "etag": None}).status_code == 400

    outside = tmp_path / "secret.md"
    outside.write_text("geheim")
    design = workspace_path(project_id) / "game-studio" / "design"
    (design / "link.md").symlink_to(outside)
    assert client.get(f"{BASE}/projects/{project_id}/design/link", headers=admin_headers).status_code == 409
    assert "link" not in [doc["slug"] for doc in client.get(f"{BASE}/projects/{project_id}/design", headers=admin_headers).json()["docs"]]

    too_big = "x" * (256 * 1024 + 1)
    assert client.put(f"{BASE}/projects/{project_id}/design/gross", headers=admin_headers,
                      json={"content": too_big, "etag": None}).status_code == 422


def test_foreign_users_cannot_read_or_write(client, admin_headers) -> None:
    project_id = _create(client, admin_headers, "Fremd")
    other = _login(client, "other")
    assert client.get(f"{BASE}/projects/{project_id}/design", headers=other).status_code == 403
    assert client.put(f"{BASE}/projects/{project_id}/design/spielidee", headers=other,
                      json={"content": "x", "etag": None}).status_code == 403
    assert client.post(f"{BASE}/projects/{project_id}/chat", headers=other).status_code == 403


def test_chat_uses_project_agent_and_reuses_session(client, admin_headers) -> None:
    project_id = _create(client, admin_headers, "Chat")
    info = client.get(f"{BASE}/projects/{project_id}/chat", headers=admin_headers).json()
    assert info["agent"] is not None
    assert info["can_start"] is True

    first = client.post(f"{BASE}/projects/{project_id}/chat", headers=admin_headers)
    assert first.status_code == 200, first.text
    assert first.json()["reused"] is False
    second = client.post(f"{BASE}/projects/{project_id}/chat", headers=admin_headers).json()
    assert second["reused"] is True
    assert second["session_id"] == first.json()["session_id"]

    from hydrahive.db import sessions as sessions_db
    session = sessions_db.get(first.json()["session_id"])
    assert session.metadata["embedded_in"] == "game-studio"
    assert session.project_id == project_id
