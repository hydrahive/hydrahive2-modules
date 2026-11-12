"""Route POST /ideas/{id}/board und der Board-Verweis in Detail, Liste, Meta und idea_read (Etappe 3a)."""
from __future__ import annotations

from helpers import BOARDS_TABLE, MOD_PREFIX, PROJECT_A, board_row, make_ctx

BASE = f"{MOD_PREFIX}/ideas"


def _new(client, headers, **body) -> dict:
    r = client.post(BASE, json={"title": "Idee", **body}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def _code(response) -> str:
    return response.json()["detail"]["code"]


def test_ohne_anmeldung_401(client):
    assert client.post(f"{BASE}/x/board").status_code == 401


def test_board_anlegen_liefert_die_idee_mit_board(client, alice):
    idea = _new(client, alice, title="Admin-Seite", body="alles an einem Ort", project_id=PROJECT_A)
    assert idea["board"] is None
    r = client.post(f"{BASE}/{idea['id']}/board", headers=alice)
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["board"] == {"id": data["board_id"], "name": "Admin-Seite", "has_proposal": False, "missing": False}
    assert (data["status"], data["body"]) == ("new", "alles an einem Ort")
    assert [n["author"] for n in data["notes"]] == ["system"]
    assert board_row(data["board_id"])["project_id"] == PROJECT_A
    assert client.get(f"{BASE}/{idea['id']}", headers=alice).json()["board"] == data["board"]


def test_zweiter_aufruf_liefert_dasselbe_board_mit_200(client, alice):
    idea = _new(client, alice)
    first = client.post(f"{BASE}/{idea['id']}/board", headers=alice)
    again = client.post(f"{BASE}/{idea['id']}/board", headers=alice)
    assert (first.status_code, again.status_code) == (201, 200)
    assert again.json()["board_id"] == first.json()["board_id"]
    assert len(again.json()["notes"]) == 1


def test_liste_zeigt_den_verweis(client, alice):
    idea = _new(client, alice)
    board_id = client.post(f"{BASE}/{idea['id']}/board", headers=alice).json()["board_id"]
    listed = client.get(f"{BASE}?status=all", headers=alice).json()["ideas"]
    assert [i["board_id"] for i in listed] == [board_id]


def test_fremde_und_unbekannte_idee_404(client, alice, bob):
    idea = _new(client, alice)
    for url in (f"{BASE}/{idea['id']}/board", f"{BASE}/gibt-es-nicht/board"):
        r = client.post(url, headers=bob)
        assert r.status_code == 404 and _code(r) == "idea_not_found"
    assert client.get(f"{BASE}/{idea['id']}", headers=alice).json()["board"] is None


def test_ohne_blueprint_modul_409_und_meta_meldet_es(client, alice, monkeypatch):
    from backend import board_link

    idea = _new(client, alice)
    assert client.get(f"{MOD_PREFIX}/meta", headers=alice).json()["blueprint_installed"] is True
    monkeypatch.setattr(board_link, "BOARDS_TABLE", "module_blueprint_gibt_es_nicht")
    assert client.get(f"{MOD_PREFIX}/meta", headers=alice).json()["blueprint_installed"] is False
    r = client.post(f"{BASE}/{idea['id']}/board", headers=alice)
    assert r.status_code == 409 and _code(r) == "blueprint_not_installed"


def test_obergrenze_409(client, alice, monkeypatch):
    from backend import board_link

    monkeypatch.setattr(board_link, "MAX_BOARDS", 1)
    assert client.post(f"{BASE}/{_new(client, alice)['id']}/board", headers=alice).status_code == 201
    r = client.post(f"{BASE}/{_new(client, alice)['id']}/board", headers=alice)
    assert r.status_code == 409 and _code(r) == "boards_full"


def test_board_id_ist_ueber_patch_nicht_setzbar(client, alice, bob):
    foreign = client.post(f"{BASE}/{_new(client, bob)['id']}/board", headers=bob).json()["board_id"]
    idea = _new(client, alice)
    client.patch(f"{BASE}/{idea['id']}", json={"board_id": foreign}, headers=alice)
    assert client.get(f"{BASE}/{idea['id']}", headers=alice).json()["board_id"] is None


def test_detail_meldet_ein_geloeschtes_board(client, alice):
    from hydrahive.db.connection import db

    idea = _new(client, alice)
    board_id = client.post(f"{BASE}/{idea['id']}/board", headers=alice).json()["board_id"]
    with db() as conn:
        conn.execute(f'DELETE FROM {BOARDS_TABLE} WHERE id = ? AND "user" = ?', (board_id, "alice"))
    board = client.get(f"{BASE}/{idea['id']}", headers=alice).json()["board"]
    assert board == {"id": board_id, "name": None, "has_proposal": False, "missing": True}


async def test_idea_read_nennt_das_board():
    from backend import board_link, store
    from backend.tools_read import READ_TOOL

    idea = store.create("alice", title="Admin-Seite")
    ohne = (await READ_TOOL.execute({"idea_id": idea["id"]}, make_ctx())).output
    assert "Board:" not in ohne
    linked, _ = board_link.create("alice", idea["id"])
    text = (await READ_TOOL.execute({"idea_id": idea["id"]}, make_ctx())).output
    assert f"Board: „Admin-Seite“ · ID {linked['board_id']}" in text
    assert "blueprint_read" in text and "blueprint_propose" in text
    assert "Vorschlag" not in text.split("Beschreibung:")[0]


async def test_idea_read_nennt_einen_offenen_vorschlag_und_ein_geloeschtes_board():
    from backend import board_link, store
    from backend.tools_read import READ_TOOL
    from hydrahive.db.connection import db

    idea = store.create("alice", title="Admin-Seite")
    linked, _ = board_link.create("alice", idea["id"])
    with db() as conn:
        conn.execute(f"UPDATE {BOARDS_TABLE} SET proposal_json = ? WHERE id = ?",
                     ('{"nodes":[],"edges":[]}', linked["board_id"]))
    text = (await READ_TOOL.execute({"idea_id": idea["id"]}, make_ctx())).output
    assert "ein Vorschlag liegt offen" in text
    with db() as conn:
        conn.execute(f'DELETE FROM {BOARDS_TABLE} WHERE id = ? AND "user" = ?', (linked["board_id"], "alice"))
    text = (await READ_TOOL.execute({"idea_id": idea["id"]}, make_ctx())).output
    assert f"Board: nicht mehr vorhanden (ID {linked['board_id']})" in text


def _line(**over) -> str:
    from backend import render

    return render.board_line({"id": 7, "name": "Name", "has_proposal": False, "missing": False, **over})


def test_boardzeile_kuerzt_lange_namen_und_bleibt_einzeilig():
    line = _line(name="N" * 900)
    assert len(line) < 320 and "blueprint_read" in line
    assert "\n" not in _line(name="Erste Zeile\nzweite Zeile")


def test_board_steht_im_text_nach_dem_task():
    from backend import render

    idea = {"id": "i" * 36, "title": "T", "status": "new", "origin": "user", "body": "",
            "created_at": "2026-11-12T10:00:00", "updated_at": "2026-11-12T10:00:00"}
    task = {"id": "t" * 36, "short_id": "t" * 8, "title": "T", "status": "open", "missing": False}
    board = {"id": 7, "name": "T", "has_proposal": False, "missing": False}
    text = render.render_idea(idea, [], None, task, board)
    assert text.index("Task:") < text.index("Board:") < text.index("Beschreibung:")
    assert "Board:" not in render.render_idea(idea, [], None, task)
