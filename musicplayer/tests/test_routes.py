"""Musicplayer-Routen — Projekt-RBAC, Upload, Liste, Stream und Download."""
from __future__ import annotations

import io

from conftest import PROJECT_A, PROJECT_B

PREFIX = "/api/modules/musicplayer"
MP3 = b"ID3\x03\x00\x00\x00\x00\x00\x00fake-mp3-bytes" + b"\x00" * 64


def _base(project_id: str = PROJECT_A) -> str:
    return f"{PREFIX}/projects/{project_id}"


def _upload(client, headers, project_id=PROJECT_A, name="song.mp3", title="", data=MP3, mime="audio/mpeg"):
    files = {"file": (name, io.BytesIO(data), mime)}
    form = {"title": title} if title else {}
    return client.post(f"{_base(project_id)}/tracks", files=files, data=form, headers=headers)


# ---------------------------------------------------------------- Auth/Projekt-RBAC
def test_list_braucht_auth(client):
    assert client.get(f"{_base()}/tracks").status_code == 401


def test_projektfremder_nutzer_erhaelt_403(client, outsider_headers):
    assert client.get(f"{_base()}/tracks", headers=outsider_headers).status_code == 403


def test_reader_kann_lesen_aber_nicht_schreiben(client, reader_headers, writer_headers):
    _upload(client, writer_headers)
    response = client.get(f"{_base()}/tracks", headers=reader_headers)

    assert response.status_code == 200
    assert len(response.json()["tracks"]) == 1
    assert response.json()["permissions"] == {"can_upload": False, "can_delete": False}
    assert _upload(client, reader_headers).status_code == 403


def test_writer_kann_hochladen_aber_nicht_loeschen(client, writer_headers):
    track_id = _upload(client, writer_headers).json()["id"]
    assert client.delete(f"{_base()}/tracks/{track_id}", headers=writer_headers).status_code == 403


def test_projektadmin_kann_loeschen(client, writer_headers, project_admin_headers):
    track_id = _upload(client, writer_headers).json()["id"]
    assert client.delete(f"{_base()}/tracks/{track_id}", headers=project_admin_headers).status_code == 200


def test_systemadmin_hat_volle_rechte(client, admin_headers):
    response = client.get(f"{_base()}/tracks", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["permissions"] == {"can_upload": True, "can_delete": True}


# ---------------------------------------------------------------- Upload + Liste
def test_upload_und_liste(client, writer_headers):
    response = _upload(client, writer_headers, name="meinsong.mp3")
    assert response.status_code == 201
    assert response.json()["title"] == "meinsong"

    tracks = client.get(f"{_base()}/tracks", headers=writer_headers).json()["tracks"]
    assert len(tracks) == 1
    assert tracks[0]["uploaded_by"] == "writer"
    assert tracks[0]["size_bytes"] == len(MP3)


def test_upload_eigener_titel(client, writer_headers):
    response = _upload(client, writer_headers, name="x.mp3", title="Mein Lieblingstrack")
    assert response.json()["title"] == "Mein Lieblingstrack"


def test_mehrere_uploads_ohne_source_im_selben_projekt(client, writer_headers):
    assert _upload(client, writer_headers, title="Erster").status_code == 201
    assert _upload(client, writer_headers, title="Zweiter").status_code == 201
    tracks = client.get(f"{_base()}/tracks", headers=writer_headers).json()["tracks"]
    assert {track["title"] for track in tracks} == {"Erster", "Zweiter"}


def test_projekte_sind_isoliert(client, admin_headers):
    _upload(client, admin_headers, project_id=PROJECT_A, title="A")
    _upload(client, admin_headers, project_id=PROJECT_B, title="B")

    tracks_a = client.get(f"{_base(PROJECT_A)}/tracks", headers=admin_headers).json()["tracks"]
    tracks_b = client.get(f"{_base(PROJECT_B)}/tracks", headers=admin_headers).json()["tracks"]
    assert [track["title"] for track in tracks_a] == ["A"]
    assert [track["title"] for track in tracks_b] == ["B"]


# ---------------------------------------------------------------- Validierung
def test_upload_kein_mp3_400(client, writer_headers):
    assert _upload(client, writer_headers, name="bild.png", mime="image/png").status_code == 400


def test_upload_leer_400(client, writer_headers):
    assert _upload(client, writer_headers, data=b"").status_code == 400


# ---------------------------------------------------------------- Streaming + Download
def test_stream_mit_header(client, writer_headers, reader_headers):
    track_id = _upload(client, writer_headers).json()["id"]
    response = client.get(f"{_base()}/tracks/{track_id}/stream", headers=reader_headers)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("audio/mpeg")
    assert response.headers["content-disposition"].startswith("inline")
    assert response.content == MP3


def test_stream_mit_token_query(client, writer_headers, reader_token):
    track_id = _upload(client, writer_headers).json()["id"]
    response = client.get(f"{_base()}/tracks/{track_id}/stream?token={reader_token}")
    assert response.status_code == 200
    assert response.content == MP3


def test_download_ist_attachment_mit_sicherem_dateinamen(client, writer_headers, reader_headers):
    track_id = _upload(client, writer_headers, title='Mein "Song"/Test').json()["id"]
    response = client.get(
        f"{_base()}/tracks/{track_id}/stream?download=1",
        headers=reader_headers,
    )
    assert response.status_code == 200
    assert response.headers["content-disposition"].startswith("attachment;")
    assert response.headers["content-disposition"].endswith('.mp3"')
    assert "/" not in response.headers["content-disposition"]
    assert response.content == MP3


def test_stream_ohne_auth_401(client, writer_headers):
    track_id = _upload(client, writer_headers).json()["id"]
    assert client.get(f"{_base()}/tracks/{track_id}/stream").status_code == 401


def test_query_token_prueft_aktuelle_projektmitgliedschaft(client, admin_headers, reader_token):
    from hydrahive.projects import config as project_config

    track_id = _upload(client, admin_headers).json()["id"]
    project = project_config.get(PROJECT_A)
    original_members = project["members"]
    project["members"] = [member for member in original_members if member["username"] != "reader"]
    project_config.update(PROJECT_A, members=project["members"])
    try:
        response = client.get(f"{_base()}/tracks/{track_id}/stream?token={reader_token}")
        assert response.status_code == 403
    finally:
        project["members"] = original_members
        project_config.update(PROJECT_A, members=project["members"])


def test_track_aus_anderem_projekt_bleibt_unsichtbar(client, admin_headers):
    track_id = _upload(client, admin_headers, project_id=PROJECT_A).json()["id"]
    response = client.get(f"{_base(PROJECT_B)}/tracks/{track_id}/stream", headers=admin_headers)
    assert response.status_code == 404


def test_stream_unbekannt_404(client, reader_headers):
    assert client.get(f"{_base()}/tracks/9999/stream", headers=reader_headers).status_code == 404


# ---------------------------------------------------------------- Delete
def test_delete_entfernt_track_und_datei(client, writer_headers, project_admin_headers):
    from backend import storage, tracks_store

    track_id = _upload(client, writer_headers).json()["id"]
    filename = tracks_store.get(PROJECT_A, track_id)["filename"]
    assert storage.file_path(PROJECT_A, filename) is not None

    response = client.delete(f"{_base()}/tracks/{track_id}", headers=project_admin_headers)
    assert response.status_code == 200
    assert client.get(f"{_base()}/tracks", headers=project_admin_headers).json()["tracks"] == []
    assert storage.file_path(PROJECT_A, filename) is None


def test_delete_unbekannt_404(client, project_admin_headers):
    assert client.delete(f"{_base()}/tracks/9999", headers=project_admin_headers).status_code == 404
