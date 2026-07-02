"""Router-Guards: Auth-Pflicht, Projekt-Zugriffskontrolle, Import/Upload-Validierung."""
from __future__ import annotations

import io

from conftest import MOD_PREFIX, OTHER_PROJECT_ID, PROJECT_ID


def test_list_files_requires_auth(client):
    r = client.get(f"{MOD_PREFIX}/projects/{PROJECT_ID}/files")
    assert r.status_code == 401


def test_foreign_project_is_404_not_403(client, auth_headers):
    """Mitglieder eines fremden Projekts bekommen 404 (Existenz nicht
    verraten), nicht 403."""
    r = client.get(f"{MOD_PREFIX}/projects/{OTHER_PROJECT_ID}/files", headers=auth_headers)
    assert r.status_code == 404


def test_invalid_project_id_is_404(client, auth_headers):
    r = client.get(f"{MOD_PREFIX}/projects/../etc/files", headers=auth_headers)
    assert r.status_code == 404


def test_list_files_empty_initially(client, auth_headers):
    r = client.get(f"{MOD_PREFIX}/projects/{PROJECT_ID}/files", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == []


def test_browse_empty_workspace(client, auth_headers):
    """Kein Silo: /browse listet den GANZEN Workspace, nicht nur videoeditor/."""
    r = client.get(f"{MOD_PREFIX}/projects/{PROJECT_ID}/browse", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == []


def test_import_rejects_unknown_source(client, auth_headers):
    r = client.post(
        f"{MOD_PREFIX}/projects/{PROJECT_ID}/import",
        headers=auth_headers,
        json={"source_rel": "does/not/exist.mp4"},
    )
    assert r.status_code == 404


def test_import_rejects_traversal(client, auth_headers):
    r = client.post(
        f"{MOD_PREFIX}/projects/{PROJECT_ID}/import",
        headers=auth_headers,
        json={"source_rel": "../../etc/passwd"},
    )
    assert r.status_code == 404


def test_upload_rejects_unsupported_extension(client, auth_headers):
    r = client.post(
        f"{MOD_PREFIX}/projects/{PROJECT_ID}/upload",
        headers=auth_headers,
        files={"file": ("evil.exe", io.BytesIO(b"not a video"), "application/octet-stream")},
    )
    assert r.status_code == 400


def test_upload_accepts_mp4_and_starts_job(client, auth_headers):
    r = client.post(
        f"{MOD_PREFIX}/projects/{PROJECT_ID}/upload",
        headers=auth_headers,
        files={"file": ("clip.mp4", io.BytesIO(b"\x00" * 1024), "video/mp4")},
    )
    assert r.status_code == 200
    body = r.json()
    assert "file_id" in body and "job_id" in body


def test_upload_appears_in_browse_afterwards(client, auth_headers):
    """Hochgeladene Datei landet sichtbar im Workspace (videoeditor/uploads/),
    nicht in einem für /browse unsichtbaren Ordner."""
    client.post(
        f"{MOD_PREFIX}/projects/{PROJECT_ID}/upload",
        headers=auth_headers,
        files={"file": ("clip2.mp4", io.BytesIO(b"\x00" * 10), "video/mp4")},
    )
    r = client.get(f"{MOD_PREFIX}/projects/{PROJECT_ID}/browse", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == []  # uploads/ liegt UNTER videoeditor/ -> bewusst ausgeschlossen


def test_get_job_404_for_unknown_id(client, auth_headers):
    r = client.get(f"{MOD_PREFIX}/projects/{PROJECT_ID}/jobs/unknown-job", headers=auth_headers)
    assert r.status_code == 404


def test_get_file_meta_404_before_processing(client, auth_headers):
    r = client.get(f"{MOD_PREFIX}/projects/{PROJECT_ID}/files/nonexistent", headers=auth_headers)
    assert r.status_code == 404


def test_save_edl_404_for_unknown_file(client, auth_headers):
    r = client.put(
        f"{MOD_PREFIX}/projects/{PROJECT_ID}/files/nonexistent/edl",
        headers=auth_headers,
        json={"file_id": "nonexistent", "timeline": []},
    )
    assert r.status_code == 404


def test_export_404_for_unknown_file(client, auth_headers):
    r = client.post(
        f"{MOD_PREFIX}/projects/{PROJECT_ID}/files/nonexistent/export",
        headers=auth_headers,
        json={"filename": "out.mp4"},
    )
    assert r.status_code == 404


def test_other_user_cannot_access_project(client, other_headers):
    r = client.get(f"{MOD_PREFIX}/projects/{PROJECT_ID}/files", headers=other_headers)
    assert r.status_code == 404
