"""Musicplayer-Routen — Upload/Guard/Liste/Stream/Delete/Validierung."""
from __future__ import annotations

import io

PREFIX = "/api/modules/musicplayer"

# Minimaler "MP3"-Inhalt — der Server prüft Endung + MIME, nicht den Bitstream.
MP3 = b"ID3\x03\x00\x00\x00\x00\x00\x00fake-mp3-bytes" + b"\x00" * 64


def _upload(client, headers, name="song.mp3", title="", data=MP3, mime="audio/mpeg"):
    files = {"file": (name, io.BytesIO(data), mime)}
    form = {"title": title} if title else {}
    return client.post(f"{PREFIX}/tracks", files=files, data=form, headers=headers)


# ---------------------------------------------------------------- Auth/Guards
def test_list_braucht_auth(client):
    assert client.get(f"{PREFIX}/tracks").status_code == 401


def test_upload_nur_admin(client, user_headers):
    assert _upload(client, user_headers).status_code == 403


def test_delete_nur_admin(client, admin_headers, user_headers):
    tid = _upload(client, admin_headers).json()["id"]
    assert client.delete(f"{PREFIX}/tracks/{tid}", headers=user_headers).status_code == 403


# ---------------------------------------------------------------- Upload + Liste
def test_upload_und_liste(client, admin_headers):
    r = _upload(client, admin_headers, name="meinsong.mp3")
    assert r.status_code == 201
    assert r.json()["title"] == "meinsong"  # .mp3 abgeschnitten
    tracks = client.get(f"{PREFIX}/tracks", headers=admin_headers).json()
    assert len(tracks) == 1
    assert tracks[0]["uploaded_by"] == "admin"
    assert tracks[0]["size_bytes"] == len(MP3)


def test_upload_eigener_titel(client, admin_headers):
    r = _upload(client, admin_headers, name="x.mp3", title="Mein Lieblingstrack")
    assert r.json()["title"] == "Mein Lieblingstrack"


def test_user_sieht_tracks(client, admin_headers, user_headers):
    _upload(client, admin_headers)
    assert len(client.get(f"{PREFIX}/tracks", headers=user_headers).json()) == 1


# ---------------------------------------------------------------- Validierung
def test_upload_kein_mp3_400(client, admin_headers):
    assert _upload(client, admin_headers, name="bild.png", mime="image/png").status_code == 400


def test_upload_leer_400(client, admin_headers):
    assert _upload(client, admin_headers, data=b"").status_code == 400


# ---------------------------------------------------------------- Streaming
def test_stream_mit_header(client, admin_headers):
    tid = _upload(client, admin_headers).json()["id"]
    r = client.get(f"{PREFIX}/tracks/{tid}/stream", headers=admin_headers)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("audio/mpeg")
    assert r.content == MP3


def test_stream_mit_token_query(client, admin_headers, admin_token):
    # <audio src> kann keinen Header setzen → Auth über ?token=
    tid = _upload(client, admin_headers).json()["id"]
    r = client.get(f"{PREFIX}/tracks/{tid}/stream?token={admin_token}")
    assert r.status_code == 200
    assert r.content == MP3


def test_stream_ohne_auth_401(client, admin_headers):
    tid = _upload(client, admin_headers).json()["id"]
    assert client.get(f"{PREFIX}/tracks/{tid}/stream").status_code == 401


def test_stream_unbekannt_404(client, admin_headers):
    assert client.get(f"{PREFIX}/tracks/9999/stream", headers=admin_headers).status_code == 404


# ---------------------------------------------------------------- Delete
def test_delete_entfernt_track_und_datei(client, admin_headers):
    from backend import storage, tracks_store
    tid = _upload(client, admin_headers).json()["id"]
    fname = tracks_store.get(tid)["filename"]
    assert storage.file_path(fname) is not None

    assert client.delete(f"{PREFIX}/tracks/{tid}", headers=admin_headers).status_code == 200
    assert client.get(f"{PREFIX}/tracks", headers=admin_headers).json() == []
    assert storage.file_path(fname) is None  # Datei weg


def test_delete_unbekannt_404(client, admin_headers):
    assert client.delete(f"{PREFIX}/tracks/9999", headers=admin_headers).status_code == 404
