"""Route POST /ideas/{id}/task und der Task-Verweis in Detail, Meta und idea_read."""
from __future__ import annotations

from helpers import MOD_PREFIX, PROJECT_A, TASKS_TABLE, make_ctx, task_row

BASE = f"{MOD_PREFIX}/ideas"


def _new(client, headers, **body) -> dict:
    r = client.post(BASE, json={"title": "Idee", **body}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def _code(response) -> str:
    return response.json()["detail"]["code"]


def test_ohne_anmeldung_401(client):
    assert client.post(f"{BASE}/x/task").status_code == 401


def test_task_anlegen_liefert_die_idee_mit_task(client, alice):
    idea = _new(client, alice, title="Admin-Seite", body="alles an einem Ort", project_id=PROJECT_A)
    assert idea["task"] is None
    r = client.post(f"{BASE}/{idea['id']}/task", headers=alice)
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["status"] == "planned"
    assert data["task"] == {"id": data["task_id"], "short_id": data["task_id"][:8], "title": "Admin-Seite",
                            "status": "open", "missing": False}
    assert [n["author"] for n in data["notes"]] == ["system"]
    assert task_row(data["task_id"])["project_id"] == PROJECT_A
    assert client.get(f"{BASE}/{idea['id']}", headers=alice).json()["task"] == data["task"]


def test_liste_zeigt_den_verweis(client, alice):
    idea = _new(client, alice)
    task_id = client.post(f"{BASE}/{idea['id']}/task", headers=alice).json()["task_id"]
    listed = client.get(f"{BASE}?status=all", headers=alice).json()["ideas"]
    assert [i["task_id"] for i in listed] == [task_id]


def test_zweiter_task_409(client, alice):
    idea = _new(client, alice)
    assert client.post(f"{BASE}/{idea['id']}/task", headers=alice).status_code == 201
    r = client.post(f"{BASE}/{idea['id']}/task", headers=alice)
    assert r.status_code == 409 and _code(r) == "task_already_linked"


def test_fremde_und_unbekannte_idee_404(client, alice, bob):
    idea = _new(client, alice)
    for url in (f"{BASE}/{idea['id']}/task", f"{BASE}/gibt-es-nicht/task"):
        r = client.post(url, headers=bob)
        assert r.status_code == 404 and _code(r) == "idea_not_found"
    assert client.get(f"{BASE}/{idea['id']}", headers=alice).json()["task"] is None


def test_ohne_tasks_modul_409_und_meta_meldet_es(client, alice, monkeypatch):
    from backend import task_link

    idea = _new(client, alice)
    monkeypatch.setattr(task_link, "TASKS_TABLE", "module_tasks_gibt_es_nicht")
    assert client.get(f"{MOD_PREFIX}/meta", headers=alice).json()["tasks_installed"] is False
    r = client.post(f"{BASE}/{idea['id']}/task", headers=alice)
    assert r.status_code == 409 and _code(r) == "tasks_not_installed"


def test_task_id_ist_ueber_patch_nicht_setzbar(client, alice, bob):
    foreign = client.post(f"{BASE}/{_new(client, bob)['id']}/task", headers=bob).json()["task_id"]
    idea = _new(client, alice)
    client.patch(f"{BASE}/{idea['id']}", json={"task_id": foreign}, headers=alice)
    assert client.get(f"{BASE}/{idea['id']}", headers=alice).json()["task_id"] is None


async def test_idea_read_nennt_titel_und_status_des_tasks():
    from backend import store, task_link
    from backend.tools_read import READ_TOOL

    idea = store.create("alice", title="Admin-Seite")
    ohne = (await READ_TOOL.execute({"idea_id": idea["id"]}, make_ctx())).output
    assert "Task:" not in ohne
    linked = task_link.create("alice", idea["id"])
    text = (await READ_TOOL.execute({"idea_id": idea["id"]}, make_ctx())).output
    assert f"Task: „Admin-Seite“ · Offen · ID {linked['task_id'][:8]}" in text
    assert "task_read" in text


async def test_idea_read_nennt_einen_geloeschten_task():
    from backend import store
    from backend.tools_read import READ_TOOL

    idea = store.create("alice", title="Task weg")
    store.update("alice", idea["id"], task_id="aaaabbbb-0000-4000-8000-000000000009")
    text = (await READ_TOOL.execute({"idea_id": idea["id"]}, make_ctx())).output
    assert "Task: nicht mehr vorhanden (ID aaaabbbb)" in text


def _line(**over) -> str:
    from backend import render

    return render.task_line({"id": "x" * 36, "short_id": "x" * 8, "title": "Titel", "status": "open", "missing": False, **over})


def test_taskzeile_kuerzt_lange_titel_und_bleibt_einzeilig():
    line = _line(title="T" * 900)
    assert len(line) < 300 and line.endswith(f"ID {'x' * 8} (Details: task_read)")
    assert "\n" not in _line(title="Erste Zeile\nzweite Zeile")


def test_taskzeile_uebersetzt_bekannte_status_und_zeigt_unbekannte_roh():
    assert "· In Arbeit ·" in _line(status="in_progress")
    assert "· Erledigt ·" in _line(status="done")
    assert "· Abgebrochen ·" in _line(status="cancelled")
    assert "· wartet ·" in _line(status="wartet")


def test_liste_traegt_die_herkunft_frueherer_tasks_nach(client, alice):
    from hydrahive.db.connection import db

    idea = client.post(f"{MOD_PREFIX}/ideas", json={"title": "Früher verknüpft"}, headers=alice).json()
    task_id = client.post(f"{MOD_PREFIX}/ideas/{idea['id']}/task", headers=alice).json()["task_id"]
    with db() as conn:
        conn.execute(f"UPDATE {TASKS_TABLE} SET source_kind = NULL, source_id = NULL WHERE id = ?", (task_id,))
    assert client.get(f"{MOD_PREFIX}/ideas", headers=alice).status_code == 200
    task = task_row(task_id)
    assert (task["source_kind"], task["source_id"]) == ("idea", idea["id"])
