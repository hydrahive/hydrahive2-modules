"""S2 Sammlung (Spec §12.1, §12.6): Liste je Kette, Fassungen, Papierkorb, endgültig löschen, Herunterladen."""
from __future__ import annotations

import pytest

from backend import store
from conftest import MOD_PREFIX, OTHER_PROJECT_ID, PROJECT_ID


def _d(title="Websuche", username="testuser", project_id=PROJECT_ID, version_of=None, html="<html>D</html>"):
    return store.create(username=username, project_id=project_id, session_id="s", agent_id=None, title=title,
                        kind="workflow", html=html, source="{}", source_ext="json", version_of=version_of)


def _ids(r):
    return [x["id"] for x in r.json()]


# --- Liste ------------------------------------------------------------------------------------------

def test_list_shows_newest_version_per_chain_with_count(client, auth_headers, store_dir):
    a = _d(title="A alt")
    b = _d(title="A neu", version_of=a["id"])
    c = _d(title="C")
    r = client.get(f"{MOD_PREFIX}/list", headers=auth_headers)
    assert r.status_code == 200
    rows = {x["id"]: x for x in r.json()}
    assert b["id"] in rows and a["id"] not in rows and c["id"] in rows
    assert rows[b["id"]]["versions"] == 2 and rows[c["id"]]["versions"] == 1
    assert rows[b["id"]]["kind"] == "workflow" and rows[b["id"]]["project_id"] == PROJECT_ID
    assert rows[b["id"]]["project_name"] == PROJECT_ID
    assert _ids(r).index(c["id"]) < _ids(r).index(b["id"]) or rows[b["id"]]["created_at"] <= rows[c["id"]]["created_at"]


def test_list_filters_by_search_and_project(client, auth_headers, admin_headers, store_dir):
    a = _d(title="Ablauf der Websuche")
    b = _d(title="Datenbank Kunden")
    c = _d(title="ohne", project_id=None)
    assert _ids(client.get(f"{MOD_PREFIX}/list?q=websuche", headers=auth_headers)) == [a["id"]]
    proj = _ids(client.get(f"{MOD_PREFIX}/list?project={PROJECT_ID}", headers=auth_headers))
    assert a["id"] in proj and b["id"] in proj and c["id"] not in proj
    assert _ids(client.get(f"{MOD_PREFIX}/list?project=none", headers=auth_headers)) == [c["id"]]


def test_list_never_shows_foreign_diagrams(client, other_headers, store_dir):
    _d()
    mine = _d(username="other", project_id=OTHER_PROJECT_ID, title="meins")
    assert _ids(client.get(f"{MOD_PREFIX}/list", headers=other_headers)) == [mine["id"]]


def test_list_trash_view(client, auth_headers, store_dir):
    a = _d()
    b = _d(title="weg")
    client.post(f"{MOD_PREFIX}/trash/{b['id']}", headers=auth_headers)
    assert _ids(client.get(f"{MOD_PREFIX}/list", headers=auth_headers)) == [a["id"]]
    assert _ids(client.get(f"{MOD_PREFIX}/list?trash=1", headers=auth_headers)) == [b["id"]]


def test_item_with_all_versions(client, auth_headers, other_headers, store_dir):
    a = _d()
    b = _d(version_of=a["id"])
    r = client.get(f"{MOD_PREFIX}/item/{b['id']}", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == b["id"] and [v["id"] for v in body["versions"]] == [a["id"], b["id"]]
    assert client.get(f"{MOD_PREFIX}/item/{b['id']}", headers=other_headers).status_code == 404


# --- Papierkorb ---------------------------------------------------------------------------------------

def test_trash_and_restore_whole_chain(client, auth_headers, store_dir):
    a = _d()
    b = _d(version_of=a["id"])
    assert client.post(f"{MOD_PREFIX}/trash/{a['id']}", headers=auth_headers).status_code == 204
    assert store.get(a["id"])["deleted_at"] and store.get(b["id"])["deleted_at"]
    assert client.post(f"{MOD_PREFIX}/restore/{b['id']}", headers=auth_headers).status_code == 204
    assert store.get(a["id"])["deleted_at"] is None and store.get(b["id"])["deleted_at"] is None


def test_project_member_who_did_not_create_cannot_trash(client, auth_headers, store_dir):
    d = _d(username="jemand")                      # im Projekt von testuser, aber nicht von ihm erstellt
    assert client.get(f"{MOD_PREFIX}/item/{d['id']}", headers=auth_headers).status_code == 200
    r = client.post(f"{MOD_PREFIX}/trash/{d['id']}", headers=auth_headers)
    assert r.status_code == 403 and r.json()["detail"]["code"] == "diagram_not_owner"
    assert store.get(d["id"])["deleted_at"] is None


def test_admin_can_trash_anything(client, admin_headers, store_dir):
    d = _d(username="other", project_id=OTHER_PROJECT_ID)
    assert client.post(f"{MOD_PREFIX}/trash/{d['id']}", headers=admin_headers).status_code == 204


def test_stranger_gets_404_not_403(client, other_headers, store_dir):
    d = _d()
    for method, path in (("post", "trash"), ("post", "restore"), ("delete", "item")):
        r = getattr(client, method)(f"{MOD_PREFIX}/{path}/{d['id']}", headers=other_headers)
        assert r.status_code == 404, path


# --- endgültig löschen --------------------------------------------------------------------------------

def test_delete_only_from_trash(client, auth_headers, store_dir):
    d = _d()
    r = client.delete(f"{MOD_PREFIX}/item/{d['id']}", headers=auth_headers)
    assert r.status_code == 409 and r.json()["detail"]["code"] == "diagram_not_in_trash"
    assert store.get(d["id"]) is not None


def test_delete_removes_whole_chain_and_files(client, auth_headers, store_dir):
    a = _d()
    b = _d(version_of=a["id"])
    keep = _d(title="bleibt")
    client.post(f"{MOD_PREFIX}/trash/{a['id']}", headers=auth_headers)
    assert client.delete(f"{MOD_PREFIX}/item/{b['id']}", headers=auth_headers).status_code == 204
    for x in (a, b):
        assert store.get(x["id"]) is None
        assert not (store_dir / x["id"]).exists()
    assert store.get(keep["id"]) is not None and (store_dir / keep["id"] / "diagramm.html").exists()


def test_delete_never_leaves_the_store_folder(client, auth_headers, store_dir, monkeypatch):
    """Auch bei manipulierter ID wird nur innerhalb von data_dir/diagramme gelöscht."""
    d = _d()
    client.post(f"{MOD_PREFIX}/trash/{d['id']}", headers=auth_headers)
    for bad in ("..", "..%2F..", "d_x%2F..%2F.."):
        assert client.delete(f"{MOD_PREFIX}/item/{bad}", headers=auth_headers).status_code == 404
    assert store_dir.exists() and (store_dir / d["id"]).exists()


# --- Herunterladen ------------------------------------------------------------------------------------

def test_download_is_attachment_with_sandbox_csp(client, auth_headers, other_headers, store_dir):
    d = _d(title="Ablauf: Websuche / Variante C", html="<html>DOWN</html>")
    r = client.get(f"{MOD_PREFIX}/download/{d['id']}", headers=auth_headers)
    assert r.status_code == 200 and r.text == "<html>DOWN</html>"
    cd = r.headers["content-disposition"]
    assert cd.startswith("attachment;") and ".html" in cd and "/" not in cd.split("filename", 1)[1]
    assert r.headers["content-security-policy"].startswith("sandbox ")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert client.get(f"{MOD_PREFIX}/download/{d['id']}", headers=other_headers).status_code == 404


@pytest.mark.parametrize(("title", "name"), [
    ("Ablauf: Websuche / Variante C", "Ablauf-Websuche-Variante-C.html"),
    ("", "diagramm.html"),
    ("../../etc/passwd", "etc-passwd.html"),
    ("Größe ÄÖÜ", "Größe-ÄÖÜ.html"),
])
def test_download_filename(title, name):
    from backend import collection
    assert collection.file_name(title) == name
