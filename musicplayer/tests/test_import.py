"""Import generierter Musik — projektlokaler Scan, RBAC, Dedup und Traversal-Schutz."""
from __future__ import annotations

import pytest

from conftest import PROJECT_A, PROJECT_B

PREFIX = "/api/modules/musicplayer"
GEN_BYTES = b"ID3generated-track" + b"\x00" * 32


def _base(project_id: str = PROJECT_A) -> str:
    return f"{PREFIX}/projects/{project_id}"


@pytest.fixture
def gen_track():
    from backend import storage

    directory = storage.project_workspace(PROJECT_A) / "generated"
    directory.mkdir(parents=True, exist_ok=True)
    file = directory / "abc123.mp3"
    file.write_bytes(GEN_BYTES)
    yield "generated/abc123.mp3"
    file.unlink(missing_ok=True)


# ---------------------------------------------------------------- Guards
def test_list_generated_braucht_write(client, reader_headers):
    assert client.get(f"{_base()}/generated", headers=reader_headers).status_code == 403


def test_import_braucht_write(client, reader_headers):
    response = client.post(
        f"{_base()}/generated/import",
        json={"path": "generated/x.mp3"},
        headers=reader_headers,
    )
    assert response.status_code == 403


def test_projektfremder_nutzer_erhaelt_403(client, outsider_headers):
    assert client.get(f"{_base()}/generated", headers=outsider_headers).status_code == 403


# ---------------------------------------------------------------- Scan
def test_scan_findet_nur_im_aktiven_projekt_generierte(client, writer_headers, gen_track):
    from backend import storage

    foreign = storage.project_workspace(PROJECT_B) / "generated" / "foreign.mp3"
    foreign.parent.mkdir(parents=True, exist_ok=True)
    foreign.write_bytes(GEN_BYTES)

    rows = client.get(f"{_base()}/generated", headers=writer_headers).json()
    assert [row["path"] for row in rows] == [gen_track]
    assert rows[0]["already_imported"] is False
    assert rows[0]["workspace"] == "generated"


# ---------------------------------------------------------------- Import (kopieren)
def test_import_kopiert_ins_projekt_und_quelle_bleibt(client, writer_headers, gen_track):
    from backend import storage, tracks_store

    source = storage.project_workspace(PROJECT_A) / gen_track
    response = client.post(
        f"{_base()}/generated/import",
        json={"path": gen_track},
        headers=writer_headers,
    )
    assert response.status_code == 201

    tracks = client.get(f"{_base()}/tracks", headers=writer_headers).json()["tracks"]
    assert len(tracks) == 1
    assert tracks[0]["title"].startswith("Generiert")
    stored = tracks_store.get(PROJECT_A, tracks[0]["id"])
    assert storage.file_path(PROJECT_A, stored["filename"]).read_bytes() == GEN_BYTES
    assert source.is_file() and source.read_bytes() == GEN_BYTES


def test_import_dedup_ist_projektgebunden(client, admin_headers, gen_track):
    payload = {"path": gen_track}
    client.post(f"{_base()}/generated/import", json=payload, headers=admin_headers)
    again = client.post(f"{_base()}/generated/import", json=payload, headers=admin_headers)
    assert again.status_code == 409
    rows = client.get(f"{_base()}/generated", headers=admin_headers).json()
    assert rows[0]["already_imported"] is True


# ---------------------------------------------------------------- Sicherheit
def test_import_traversal_404(client, writer_headers):
    response = client.post(
        f"{_base()}/generated/import",
        json={"path": "../../../etc/passwd"},
        headers=writer_headers,
    )
    assert response.status_code in (404, 422)


def test_import_nicht_generated_404(client, writer_headers):
    from backend import storage

    file = storage.project_workspace(PROJECT_A) / "loose.mp3"
    file.write_bytes(b"x")
    response = client.post(
        f"{_base()}/generated/import",
        json={"path": "loose.mp3"},
        headers=writer_headers,
    )
    file.unlink(missing_ok=True)
    assert response.status_code == 404


def test_import_aus_anderem_projekt_404(client, writer_headers):
    from backend import storage

    file = storage.project_workspace(PROJECT_B) / "generated" / "foreign.mp3"
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_bytes(GEN_BYTES)
    response = client.post(
        f"{_base(PROJECT_A)}/generated/import",
        json={"path": f"../{PROJECT_B}/generated/foreign.mp3"},
        headers=writer_headers,
    )
    assert response.status_code == 404
