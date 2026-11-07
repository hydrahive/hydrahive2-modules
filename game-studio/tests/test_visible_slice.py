from __future__ import annotations

from hydrahive.projects import config as project_config
from hydrahive.projects._paths import workspace_path

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


def _project(title: str = "Leuchtturm im Sturm", engine: str = "godot", engine_version: str = "auto") -> dict:
    return {
        "entry_kind": "new",
        "engine": engine,
        "engine_version": engine_version,
        "title": title,
        "idea": "Der Spieler hält ein Leuchtfeuer während eines Sturms am Leben.",
        "genre": "Puzzle-Abenteuer",
        "target_platform": "desktop",
    }


def test_routes_require_auth_and_project_creation_requires_admin(client, auth_headers) -> None:
    assert client.get(f"{BASE}/overview").status_code in (401, 403)
    denied = client.post(f"{BASE}/projects", headers=auth_headers, json=_project())
    assert denied.status_code == 403


def test_overview_starts_without_demo_projects_and_reports_real_sharing(client, auth_headers) -> None:
    response = client.get(f"{BASE}/overview", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["projects"] == []
    assert body["sharing"] == {
        "available": True,
        "running": True,
        "user": "test-share",
        "platform": "linux",
    }
    assert "workstation" not in body
    assert "runner" not in body


def test_project_is_canonical_in_workspace_and_shared_for_selected_engine(client, admin_headers) -> None:
    response = client.post(f"{BASE}/projects", headers=admin_headers, json=_project(engine="unity"))
    assert response.status_code == 201, response.text
    project = response.json()
    project_id = project["project_id"]

    assert project["engine"] == "unity"
    assert project["sharing"]["enabled"] is True
    assert project["sharing"]["share_name"].startswith("game_")
    assert project["sharing"]["user"] == "test-share"
    root = workspace_path(project_id)
    assert (root / "game-studio" / "project.json").is_file()
    assert "unity" in (root / "game-studio" / "project.json").read_text()
    assert "Leuchtturm" in (root / "game-studio" / "game-brief.md").read_text()
    assert (root / ".git").is_dir()

    config = project_config.get(project_id)
    assert config is not None
    assert config["metadata"]["game_studio"] == {"schema_version": 1}
    assert config["samba_enabled"] is True


def test_workspace_project_survives_steps_and_uses_optimistic_revision(client, admin_headers) -> None:
    created = client.post(f"{BASE}/projects", headers=admin_headers, json=_project(engine="unreal")).json()
    project_id = created["project_id"]

    skipped = client.patch(
        f"{BASE}/projects/{project_id}", headers=admin_headers,
        json={"revision": 1, "current_step": 4},
    )
    assert skipped.status_code == 400
    assert client.patch(
        f"{BASE}/projects/{project_id}", headers=admin_headers,
        json={"revision": 1, "current_step": 5},
    ).status_code == 422

    updated_response = client.patch(
        f"{BASE}/projects/{project_id}",
        headers=admin_headers,
        json={
            "revision": 1,
            "core_action": "Brennstoff verteilen und das Licht ausrichten.",
            "success_condition": "Das Schiff erreicht sichtbar den sicheren Hafen.",
            "current_step": 4,
        },
    )
    assert updated_response.status_code == 200, updated_response.text
    updated = updated_response.json()
    assert updated["revision"] == 2
    assert updated["current_step"] == 4
    assert "Brennstoff" in (workspace_path(project_id) / "game-studio" / "vertical-slice.md").read_text()

    conflict = client.patch(
        f"{BASE}/projects/{project_id}", headers=admin_headers,
        json={"revision": 1, "title": "Veraltete Änderung"},
    )
    assert conflict.status_code == 409


def test_unreal_generator_creates_real_version_neutral_cpp_project(client, admin_headers) -> None:
    created = client.post(
        f"{BASE}/projects", headers=admin_headers,
        json=_project(title="Hafen Wächter 2", engine="unreal", engine_version="5.5"),
    ).json()
    project_id = created["project_id"]
    assert created["engine_version"] == "5.5"
    assert created["engine_project_ready"] is False
    assert created["engine_project_name"] == "HafenWachter2"

    prepared = client.patch(
        f"{BASE}/projects/{project_id}", headers=admin_headers,
        json={
            "revision": 1,
            "core_action": "Mit WASD zum Leuchtfeuer laufen und springen.",
            "success_condition": "Am Ziel erscheint sichtbar Ziel erreicht.",
            "current_step": 4,
        },
    ).json()
    generated_response = client.post(
        f"{BASE}/projects/{project_id}/unreal-project", headers=admin_headers,
        json={"revision": prepared["revision"]},
    )
    assert generated_response.status_code == 200, generated_response.text
    generated = generated_response.json()
    assert generated["engine_project_ready"] is True
    assert generated["engine_project_path"] == "unreal/HafenWachter2/HafenWachter2.uproject"
    assert generated["revision"] == 3

    root = workspace_path(project_id) / "unreal" / "HafenWachter2"
    descriptor = (root / "HafenWachter2.uproject").read_text()
    assert '"EngineAssociation"' not in descriptor
    assert '"Name": "HafenWachter2"' in descriptor
    character = (root / "Source" / "HafenWachter2" / "HafenWachter2Character.cpp").read_text()
    assert "AddControllerYawInput" in character
    assert "MouseX" in (root / "Config" / "DefaultInput.ini").read_text()
    assert (root / "Source" / "HafenWachter2" / "HafenWachter2GameMode.cpp").is_file()
    assert (root / "Source" / "HafenWachter2" / "HafenWachter2Goal.cpp").is_file()
    assert (root / "Config" / "DefaultEngine.ini").is_file()
    assert (root / "Config" / "DefaultInput.ini").is_file()
    assert (root / ".game-studio-generated.json").is_file()
    assert not (root / "Scripts").exists()
    targets = (root / "Source" / "HafenWachter2.Target.cs").read_text()
    assert "BuildSettingsVersion" not in targets
    assert "IncludeOrderVersion" not in targets

    descriptor_path = root / "HafenWachter2.uproject"
    descriptor_path.write_text("USER MODIFIED PROJECT FILE\n")
    missing_source = root / "Source" / "HafenWachter2" / "HafenWachter2Goal.cpp"
    missing_source.unlink()
    repeated = client.post(
        f"{BASE}/projects/{project_id}/unreal-project", headers=admin_headers,
        json={"revision": generated["revision"]},
    )
    assert repeated.status_code == 200
    assert repeated.json()["revision"] == generated["revision"]
    assert descriptor_path.read_text() == "USER MODIFIED PROJECT FILE\n"
    assert missing_source.is_file()


def test_unreal_generator_never_overwrites_existing_project_files(client, admin_headers) -> None:
    created = client.post(
        f"{BASE}/projects", headers=admin_headers,
        json=_project(title="Vorhandenes Projekt", engine="unreal"),
    ).json()
    project_id = created["project_id"]
    prepared = client.patch(
        f"{BASE}/projects/{project_id}", headers=admin_headers,
        json={
            "revision": 1,
            "core_action": "Laufen",
            "success_condition": "Ziel erreichen",
            "current_step": 4,
        },
    ).json()
    descriptor = workspace_path(project_id) / created["engine_project_path"]
    descriptor.parent.mkdir(parents=True)
    descriptor.write_text("USER FILE\n")

    response = client.post(
        f"{BASE}/projects/{project_id}/unreal-project", headers=admin_headers,
        json={"revision": prepared["revision"]},
    )
    assert response.status_code == 409
    assert descriptor.read_text() == "USER FILE\n"
    assert not (descriptor.parent / "Source").exists()


def test_unreal_generator_rejects_workspace_symlink(client, admin_headers, tmp_path) -> None:
    created = client.post(
        f"{BASE}/projects", headers=admin_headers,
        json=_project(title="Symlink Test", engine="unreal"),
    ).json()
    project_id = created["project_id"]
    prepared = client.patch(
        f"{BASE}/projects/{project_id}", headers=admin_headers,
        json={
            "revision": 1,
            "core_action": "Laufen",
            "success_condition": "Ziel erreichen",
            "current_step": 4,
        },
    ).json()
    outside = tmp_path / "outside"
    outside.mkdir()
    (workspace_path(project_id) / "unreal").symlink_to(outside, target_is_directory=True)

    response = client.post(
        f"{BASE}/projects/{project_id}/unreal-project", headers=admin_headers,
        json={"revision": prepared["revision"]},
    )
    assert response.status_code == 409
    assert list(outside.iterdir()) == []


def test_invalid_local_result_is_not_exposed(client, admin_headers) -> None:
    created = client.post(
        f"{BASE}/projects", headers=admin_headers,
        json=_project(title="Result Test", engine="unreal"),
    ).json()
    root = workspace_path(created["project_id"])
    results = root / "game-studio" / "results"
    results.mkdir()
    (results / "unreal-build.json").write_text(
        '{"schema_version":1,"kind":"unreal-build","status":"passed","exit_code":0,'
        '"finished_at":"2026-11-07T10:00:00Z","log_path":"../../etc/passwd"}\n'
    )

    project = client.get(f"{BASE}/projects/{created['project_id']}", headers=admin_headers).json()
    assert project["last_engine_run"] is None


def test_project_access_uses_core_project_roles(client, admin_headers) -> None:
    project_id = client.post(f"{BASE}/projects", headers=admin_headers, json=_project()).json()["project_id"]
    other = _login(client, "other")

    assert client.get(f"{BASE}/projects/{project_id}", headers=other).status_code == 403
    assert client.patch(
        f"{BASE}/projects/{project_id}", headers=other,
        json={"revision": 1, "title": "Fremd"},
    ).status_code == 403
    assert client.post(
        f"{BASE}/projects/{project_id}/unreal-project", headers=other,
        json={"revision": 1},
    ).status_code == 403


def test_samba_failure_compensates_new_core_project(client, admin_headers, monkeypatch) -> None:
    from backend import projects

    before = {item["id"] for item in project_config.list_all()}
    monkeypatch.setattr(projects, "enable_share", lambda project_id, name: (False, "samba_not_installed"))
    response = client.post(f"{BASE}/projects", headers=admin_headers, json=_project("Rollback"))

    assert response.status_code == 400
    assert {item["id"] for item in project_config.list_all()} == before


def test_sqlite_content_table_is_removed_and_schemas_are_strict(client, admin_headers) -> None:
    from hydrahive.db.connection import db

    with db() as conn:
        table = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'module_game_studio_drafts'"
        ).fetchone()
    assert table is None

    unknown = _project()
    unknown["shell"] = "unreal-editor"
    assert client.post(f"{BASE}/projects", headers=admin_headers, json=unknown).status_code == 422
    assert client.post(f"{BASE}/projects", headers=admin_headers, json=_project("   ")).status_code == 422
    assert client.post(f"{BASE}/projects", headers=admin_headers, json=_project(engine="cryengine")).status_code == 422
    assert client.post(
        f"{BASE}/projects", headers=admin_headers, json=_project(engine="unreal", engine_version="latest")
    ).status_code == 422
    assert client.post(
        f"{BASE}/projects", headers=admin_headers, json=_project(engine="unity", engine_version="5.5")
    ).status_code == 422
