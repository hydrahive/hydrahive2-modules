"""HTTP: Login, Projekt-Mitgliedschaft, 409 bei veralteter Version, Ablauf Buch → Szene → Struktur."""
from __future__ import annotations

from conftest import MOD_PREFIX, OTHER_PROJECT_ID, PROJECT_ID

P = f"{MOD_PREFIX}/projects/{PROJECT_ID}"


def _book(client, headers, **kw):
    r = client.post(f"{P}/books", json={"title": "Bienen", "kind": "nonfiction", "language": "de", **kw}, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def test_needs_login(client):
    assert client.get(f"{P}/books").status_code in (401, 403)


def test_foreign_project_is_404(client, auth_headers, other_headers):
    b = _book(client, auth_headers)
    assert client.get(f"{P}/books", headers=other_headers).status_code == 404
    assert client.get(f"{P}/books/{b['id']}", headers=other_headers).status_code == 404
    assert client.get(f"{MOD_PREFIX}/projects/{OTHER_PROJECT_ID}/books", headers=auth_headers).status_code == 404
    assert client.get(f"{MOD_PREFIX}/projects/..%2F..%2Fetc/books", headers=auth_headers).status_code == 404


def test_full_flow_and_conflict(client, auth_headers):
    b = _book(client, auth_headers)
    full = client.get(f"{P}/books/{b['id']}", headers=auth_headers).json()
    assert full["book"]["title"] == "Bienen" and full["structure"]["parts"][0]["chapters"][0]["title"] == "Kapitel 1"
    sid = full["structure"]["parts"][0]["chapters"][0]["scenes"][0]
    sc = full["scenes"][sid]
    assert sc["title"] == "Abschnitt 1" and sc["text"] == "" and sc["version"] == 1

    r = client.put(f"{P}/books/{b['id']}/scenes/{sid}", json={"text": "Die Königin.", "base_version": 1}, headers=auth_headers)
    assert r.status_code == 200 and r.json()["version"] == 2
    stale = client.put(f"{P}/books/{b['id']}/scenes/{sid}", json={"text": "alt", "base_version": 1}, headers=auth_headers)
    assert stale.status_code == 409
    assert stale.json()["detail"]["current"]["text"] == "Die Königin."


def test_book_list_and_patch_and_delete(client, auth_headers):
    b = _book(client, auth_headers)
    lst = client.get(f"{P}/books", headers=auth_headers).json()
    assert [x["id"] for x in lst] == [b["id"]] and "words" in lst[0]
    r = client.patch(f"{P}/books/{b['id']}", json={"title": "Bienenvolk", "model": "x/y", "base_version": b["version"]}, headers=auth_headers)
    assert r.status_code == 200 and r.json()["title"] == "Bienenvolk" and r.json()["model"] == "x/y"
    stale = client.patch(f"{P}/books/{b['id']}", json={"notes": "veraltet", "base_version": b["version"]}, headers=auth_headers)
    assert stale.status_code == 409 and stale.json()["detail"]["current"]["title"] == "Bienenvolk"
    assert client.get(f"{P}/books/{b['id']}", headers=auth_headers).json()["book"]["notes"] == ""
    assert client.delete(f"{P}/books/{b['id']}", headers=auth_headers).status_code == 200
    assert client.get(f"{P}/books", headers=auth_headers).json() == []


def test_add_scene_structure_and_snapshots(client, auth_headers):
    b = _book(client, auth_headers, kind="novel")
    st = client.get(f"{P}/books/{b['id']}", headers=auth_headers).json()["structure"]
    ch = st["parts"][0]["chapters"][0]["id"]
    r = client.post(f"{P}/books/{b['id']}/scenes", json={"chapter_id": ch, "title": "Szene 2"}, headers=auth_headers)
    assert r.status_code == 200
    sid = r.json()["scene"]["id"]
    st = client.get(f"{P}/books/{b['id']}", headers=auth_headers).json()["structure"]
    first, second = st["parts"][0]["chapters"][0]["scenes"]
    assert second == sid
    st["parts"][0]["chapters"][0]["scenes"] = [second, first]
    r = client.put(f"{P}/books/{b['id']}/structure", json={"structure": st, "base_version": st["version"]}, headers=auth_headers)
    assert r.status_code == 200 and r.json()["parts"][0]["chapters"][0]["scenes"] == [second, first]
    assert client.post(f"{P}/books/{b['id']}/scenes/{first}/snapshots", headers=auth_headers).status_code == 200
    snaps = client.get(f"{P}/books/{b['id']}/scenes/{first}/snapshots", headers=auth_headers).json()
    assert len(snaps) == 1 and set(snaps[0]) >= {"id", "at", "words"}


def test_bad_input_is_400_not_500(client, auth_headers):
    assert client.post(f"{P}/books", json={"title": "", "kind": "novel", "language": "de"}, headers=auth_headers).status_code in (400, 422)
    b = _book(client, auth_headers)
    assert client.get(f"{P}/books/{b['id']}/scenes/{'z' * 32}/snapshots", headers=auth_headers).status_code == 404
    assert client.get(f"{P}/books/{'0' * 32}", headers=auth_headers).status_code == 404


def test_reader_may_read_but_not_change(client, auth_headers, reader_headers):
    """Projektrolle „read“: Liste/Öffnen/Schnappschüsse lesen ja; schreiben, anlegen, KI nein (403)."""
    b = _book(client, auth_headers)
    full = client.get(f"{P}/books/{b['id']}", headers=reader_headers)
    assert full.status_code == 200
    sid = full.json()["structure"]["parts"][0]["chapters"][0]["scenes"][0]
    assert client.get(f"{P}/books", headers=reader_headers).status_code == 200
    assert client.get(f"{P}/books/{b['id']}/scenes/{sid}/snapshots", headers=reader_headers).status_code == 200
    denied = [
        client.post(f"{P}/books", json={"title": "X", "kind": "novel"}, headers=reader_headers),
        client.put(f"{P}/books/{b['id']}/scenes/{sid}", json={"text": "fremd", "base_version": 1}, headers=reader_headers),
        client.patch(f"{P}/books/{b['id']}", json={"title": "fremd", "base_version": 1}, headers=reader_headers),
        client.delete(f"{P}/books/{b['id']}", headers=reader_headers),
        client.post(f"{P}/books/{b['id']}/scenes/{sid}/snapshots", json={}, headers=reader_headers),
        client.post(f"{P}/books/{b['id']}/ai/suggest", json={"scene_id": sid, "action": "continue"}, headers=reader_headers),
    ]
    assert [r.status_code for r in denied] == [403] * len(denied)
    assert denied[0].json()["detail"]["code"] == "project_read_only"
    assert client.get(f"{P}/books/{b['id']}", headers=auth_headers).json()["scenes"][sid]["text"] == ""


def test_system_admin_reaches_every_project_but_not_missing_ones(client, auth_headers, admin_headers):
    """Wie im Kern: System-Admin darf in jedes Projekt, auch ohne Mitglied zu sein; unbekanntes Projekt bleibt 404."""
    b = _book(client, auth_headers)
    assert client.get(f"{P}/books/{b['id']}", headers=admin_headers).status_code == 200
    assert client.post(f"{MOD_PREFIX}/projects/{OTHER_PROJECT_ID}/books", json={"title": "A", "kind": "novel"}, headers=admin_headers).status_code == 200
    assert client.get(f"{MOD_PREFIX}/projects/gibt-es-nicht-123/books", headers=admin_headers).status_code == 404
