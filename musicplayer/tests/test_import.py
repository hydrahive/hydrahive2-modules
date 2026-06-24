"""Import generierter Musik — Scan, Import, Dedup, Guards, Traversal-Schutz."""
from __future__ import annotations

import pytest

PREFIX = "/api/modules/musicplayer"
GEN_BYTES = b"ID3generated-track" + b"\x00" * 32


@pytest.fixture
def gen_track():
    """Legt ein generiertes MP3 unter workspaces/projects/<id>/generated/ an."""
    from backend import storage
    d = storage.workspaces_root() / "projects" / "019efake1234" / "generated"
    d.mkdir(parents=True, exist_ok=True)
    f = d / "abc123.mp3"
    f.write_bytes(GEN_BYTES)
    rel = str(f.relative_to(storage.workspaces_root()))
    yield rel
    f.unlink(missing_ok=True)


# ---------------------------------------------------------------- Guards
def test_list_generated_nur_admin(client, user_headers):
    assert client.get(f"{PREFIX}/generated", headers=user_headers).status_code == 403


def test_import_nur_admin(client, user_headers):
    r = client.post(f"{PREFIX}/generated/import", json={"path": "x"}, headers=user_headers)
    assert r.status_code == 403


# ---------------------------------------------------------------- Scan
def test_scan_findet_generierte(client, admin_headers, gen_track):
    rows = client.get(f"{PREFIX}/generated", headers=admin_headers).json()
    paths = [r["path"] for r in rows]
    assert gen_track in paths
    row = next(r for r in rows if r["path"] == gen_track)
    assert row["already_imported"] is False
    assert row["workspace"].startswith("projects/")


# ---------------------------------------------------------------- Import (kopieren)
def test_import_kopiert_und_quelle_bleibt(client, admin_headers, gen_track):
    from backend import storage
    src = storage.workspaces_root() / gen_track

    r = client.post(f"{PREFIX}/generated/import", json={"path": gen_track}, headers=admin_headers)
    assert r.status_code == 201

    # Track ist im Pool
    tracks = client.get(f"{PREFIX}/tracks", headers=admin_headers).json()
    assert len(tracks) == 1
    assert tracks[0]["title"].startswith("Generiert")
    # Quelldatei bleibt unangetastet
    assert src.is_file() and src.read_bytes() == GEN_BYTES


def test_import_dedup(client, admin_headers, gen_track):
    client.post(f"{PREFIX}/generated/import", json={"path": gen_track}, headers=admin_headers)
    # erneut → 409, und in der Liste markiert
    again = client.post(f"{PREFIX}/generated/import", json={"path": gen_track}, headers=admin_headers)
    assert again.status_code == 409
    rows = client.get(f"{PREFIX}/generated", headers=admin_headers).json()
    assert next(r for r in rows if r["path"] == gen_track)["already_imported"] is True


# ---------------------------------------------------------------- Sicherheit
def test_import_traversal_404(client, admin_headers):
    r = client.post(f"{PREFIX}/generated/import",
                    json={"path": "../../../etc/passwd"}, headers=admin_headers)
    assert r.status_code in (404, 422)


def test_import_nicht_generated_404(client, admin_headers):
    # Eine mp3 außerhalb eines generated-Ordners darf nicht importierbar sein
    from backend import storage
    d = storage.workspaces_root() / "projects" / "019efake1234"
    d.mkdir(parents=True, exist_ok=True)
    f = d / "loose.mp3"
    f.write_bytes(b"x")
    rel = str(f.relative_to(storage.workspaces_root()))
    r = client.post(f"{PREFIX}/generated/import", json={"path": rel}, headers=admin_headers)
    f.unlink(missing_ok=True)
    assert r.status_code == 404
