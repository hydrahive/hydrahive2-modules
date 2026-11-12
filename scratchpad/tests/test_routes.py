"""Routen des Ideen-Moduls unter /api/modules/scratchpad."""
from __future__ import annotations

import pytest
from helpers import MOD_PREFIX, PROJECT_A, PROJECT_B

BASE = f"{MOD_PREFIX}/ideas"


def _new(client, headers, **body) -> dict:
    r = client.post(BASE, json={"title": "Idee", **body}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def _code(response) -> str:
    return response.json()["detail"]["code"]


@pytest.mark.parametrize("method,path", [
    ("get", "/meta"), ("get", "/ideas"), ("post", "/ideas"), ("get", "/ideas/x"),
    ("patch", "/ideas/x"), ("delete", "/ideas/x"), ("delete", "/ideas/x/notes/1"),
])
def test_ohne_anmeldung_401(client, method, path):
    assert getattr(client, method)(MOD_PREFIX + path).status_code == 401


def test_meta(client, alice):
    data = client.get(f"{MOD_PREFIX}/meta", headers=alice).json()
    assert data["statuses"] == ["new", "review", "planned", "parked", "done", "dropped"]
    assert data["open_statuses"] == ["new", "review", "planned"]
    assert data["tasks_installed"] is True and data["blueprint_installed"] is False
    assert data["limits"] == {"title": 200, "body": 50000, "ideas": 2000}


def test_anlegen_und_lesen(client, alice):
    idea = _new(client, alice, title="  Admin-Seite  ", body="alles an einem Ort", project_id=PROJECT_A)
    assert idea["title"] == "Admin-Seite" and idea["status"] == "new" and idea["origin"] == "user"
    got = client.get(f"{BASE}/{idea['id']}", headers=alice).json()
    assert got["body"] == "alles an einem Ort" and got["project_id"] == PROJECT_A
    assert got["notes"] == []
    assert "username" not in got


def test_anlegen_ohne_beschreibung_und_ohne_projekt(client, alice):
    idea = _new(client, alice, title="Nur Kopfzeile")
    assert idea["body"] == "" and idea["project_id"] is None


def test_anlegen_in_fremdem_projekt_404(client, alice):
    r = client.post(BASE, json={"title": "Fremd", "project_id": PROJECT_B}, headers=alice)
    assert r.status_code == 404 and _code(r) == "project_not_found"


def test_admin_darf_in_jedes_projekt(client, root):
    assert _new(client, root, project_id=PROJECT_B)["project_id"] == PROJECT_B


@pytest.mark.parametrize("body", [{"title": ""}, {"title": "   "}, {"title": "x" * 201}, {"title": "ok", "body": "x" * 50_001}, {}])
def test_anlegen_mit_ungueltigen_feldern_422(client, alice, body):
    assert client.post(BASE, json=body, headers=alice).status_code == 422


def test_liste_mit_filter_und_zaehlung(client, alice):
    a = _new(client, alice, title="A", project_id=PROJECT_A)
    _new(client, alice, title="Frei")
    client.patch(f"{BASE}/{a['id']}", json={"status": "done"}, headers=alice)
    data = client.get(BASE, headers=alice).json()
    assert [i["title"] for i in data["ideas"]] == ["A", "Frei"]
    assert data["counts"]["new"] == 1 and data["counts"]["done"] == 1
    assert "body" not in data["ideas"][0] and "body_preview" in data["ideas"][0]
    only = lambda query: [i["title"] for i in client.get(f"{BASE}?{query}", headers=alice).json()["ideas"]]
    assert only(f"project_id={PROJECT_A}") == ["A"]
    assert only("project_id=none") == ["Frei"]
    assert only("status=open") == ["Frei"]
    assert only("status=done") == ["A"]
    assert only("status=all") == ["A", "Frei"]


def test_zaehlung_folgt_dem_projektfilter_nicht_dem_statusfilter(client, alice):
    _new(client, alice, title="A", project_id=PROJECT_A)
    _new(client, alice, title="Frei")
    data = client.get(f"{BASE}?project_id={PROJECT_A}&status=done", headers=alice).json()
    assert data["ideas"] == [] and data["counts"]["new"] == 1


def test_liste_mit_ungueltigem_status_422(client, alice):
    assert client.get(f"{BASE}?status=fertig", headers=alice).status_code == 422


def test_aendern(client, alice):
    idea = _new(client, alice, title="Alt", project_id=PROJECT_A)
    r = client.patch(f"{BASE}/{idea['id']}", json={"title": "Neu", "body": "Text", "status": "parked"}, headers=alice)
    assert r.status_code == 200
    data = r.json()
    assert (data["title"], data["body"], data["status"], data["project_id"]) == ("Neu", "Text", "parked", PROJECT_A)
    assert "notes" in data
    cleared = client.patch(f"{BASE}/{idea['id']}", json={"project_id": None}, headers=alice).json()
    assert cleared["project_id"] is None and cleared["title"] == "Neu"


def test_aendern_mit_ungueltigen_werten(client, alice):
    idea = _new(client, alice)
    url = f"{BASE}/{idea['id']}"
    assert client.patch(url, json={"status": "fertig"}, headers=alice).status_code == 422
    assert client.patch(url, json={"title": "  "}, headers=alice).status_code == 422
    r = client.patch(url, json={"project_id": PROJECT_B}, headers=alice)
    assert r.status_code == 404 and _code(r) == "project_not_found"
    assert client.get(url, headers=alice).json()["project_id"] is None


def test_herkunft_und_verweise_sind_ueber_die_route_nicht_setzbar(client, alice):
    idea = _new(client, alice, origin="agent", task_id="t-1", board_id=7)
    assert idea["origin"] == "user" and idea["task_id"] is None and idea["board_id"] is None
    client.patch(f"{BASE}/{idea['id']}", json={"origin": "agent", "task_id": "t-1"}, headers=alice)
    got = client.get(f"{BASE}/{idea['id']}", headers=alice).json()
    assert got["origin"] == "user" and got["task_id"] is None


def test_fremde_idee_404(client, alice, bob):
    idea = _new(client, alice, title="Privat")
    url = f"{BASE}/{idea['id']}"
    for response in (client.get(url, headers=bob), client.patch(url, json={"title": "X"}, headers=bob),
                     client.delete(url, headers=bob)):
        assert response.status_code == 404 and _code(response) == "idea_not_found"
    assert client.get(BASE, headers=bob).json()["ideas"] == []
    assert client.get(url, headers=alice).json()["title"] == "Privat"


def test_loeschen(client, alice):
    idea = _new(client, alice)
    assert client.delete(f"{BASE}/{idea['id']}", headers=alice).json() == {"removed": True}
    assert client.get(f"{BASE}/{idea['id']}", headers=alice).status_code == 404


def test_anmerkung_loeschen(client, alice, bob):
    from backend import notes

    idea = _new(client, alice)
    note = notes.add("alice", idea["id"], author="agent", body="Vorschlag", agent_name="Buddy")
    url = f"{BASE}/{idea['id']}/notes/{note['id']}"
    got = client.get(f"{BASE}/{idea['id']}", headers=alice).json()
    assert [(n["body"], n["agent_name"]) for n in got["notes"]] == [("Vorschlag", "Buddy")]
    assert client.delete(url, headers=bob).status_code == 404
    assert client.delete(url, headers=alice).json() == {"removed": True}
    r = client.delete(url, headers=alice)
    assert r.status_code == 404 and _code(r) == "note_not_found"


def test_obergrenze_409(client, alice, monkeypatch):
    from backend import store

    monkeypatch.setattr(store, "MAX_IDEAS", 1)
    _new(client, alice)
    r = client.post(BASE, json={"title": "Zu viel"}, headers=alice)
    assert r.status_code == 409 and _code(r) == "ideas_full"


def test_erste_liste_uebernimmt_die_alten_dateien(client, bob):
    from _hh_isolation import remove_test_tree
    from hydrahive.settings import settings

    folder = settings.data_dir / "scratchpad" / "bob"
    folder.mkdir(parents=True, exist_ok=True)
    try:
        (folder / "user.md").write_text("# Alte Idee\nText\n", encoding="utf-8")
        data = client.get(BASE, headers=bob).json()
        assert [(i["title"], i["origin"]) for i in data["ideas"]] == [("Alte Idee", "user")]
        assert (folder / "user.md.imported").exists()
        assert len(client.get(BASE, headers=bob).json()["ideas"]) == 1
    finally:
        remove_test_tree(folder)
