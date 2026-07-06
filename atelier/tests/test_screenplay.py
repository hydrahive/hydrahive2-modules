"""Atelier — Regie E1: Screenplay-Kopf + Szenen (CRUD, Reorder) + Routen-Guard."""
from __future__ import annotations

from backend import screenplay, storage
from conftest import OTHER_PROJECT_ID, PROJECT_ID

PREFIX = f"/api/modules/atelier/projects/{PROJECT_ID}"
OTHER_PREFIX = f"/api/modules/atelier/projects/{OTHER_PROJECT_ID}"


# ----------------------------------------------------------------- Task 1: Storage
def test_screenplay_dir_unter_root():
    root = storage.atelier_root(PROJECT_ID)
    d = storage.screenplay_dir(PROJECT_ID)
    assert d.is_dir()
    assert d.resolve().is_relative_to(root.resolve())


def test_scenes_dir_unter_screenplay():
    d = storage.scenes_dir(PROJECT_ID)
    assert d.is_dir()
    assert d.resolve().is_relative_to(storage.screenplay_dir(PROJECT_ID).resolve())


# ----------------------------------------------------------------- Task 2: Kopf CRUD
def test_screenplay_default_wenn_leer():
    sp = screenplay.get_screenplay(PROJECT_ID)
    assert sp["title"] == ""
    assert sp["scene_order"] == []
    assert sp["aspect_ratio"]  # nicht-leerer Default


def test_screenplay_save_und_load():
    saved = screenplay.save_screenplay(PROJECT_ID, {
        "title": "Der letzte Ritter",
        "logline": "Ein Ritter kehrt heim.",
        "description": "Düsterer Fantasy-Kurzfilm.",
        "film_model": "google/veo-3.1",
        "audio_model": "google/lyria-3-pro-preview",
        "aspect_ratio": "16:9",
        "default_duration": 8,
    })
    assert saved["title"] == "Der letzte Ritter"
    assert saved["default_duration"] == 8
    assert "updated_at" in saved
    again = screenplay.get_screenplay(PROJECT_ID)
    assert again["film_model"] == "google/veo-3.1"


def test_screenplay_sanitize_limits():
    saved = screenplay.save_screenplay(PROJECT_ID, {
        "title": "x" * 999,
        "default_duration": 9999,      # → auf max geklemmt
    })
    assert len(saved["title"]) <= 200
    assert 1 <= saved["default_duration"] <= 60


# ----------------------------------------------------------------- Task 3: Szenen CRUD
def test_scene_create_haengt_an_order():
    s = screenplay.create_scene(PROJECT_ID, {"title": "Szene 1", "description": "Ruinentor"})
    assert storage.is_valid_id(s["id"])
    sp = screenplay.get_screenplay(PROJECT_ID)
    assert s["id"] in sp["scene_order"]


def test_scene_list_folgt_order():
    a = screenplay.create_scene(PROJECT_ID, {"title": "A"})
    b = screenplay.create_scene(PROJECT_ID, {"title": "B"})
    ids = [s["id"] for s in screenplay.list_scenes(PROJECT_ID)]
    assert ids == [a["id"], b["id"]]


def test_scene_update_merged():
    s = screenplay.create_scene(PROJECT_ID, {"title": "alt", "description": "d"})
    upd = screenplay.update_scene(PROJECT_ID, s["id"], {"title": "neu"})
    assert upd["title"] == "neu"
    assert upd["description"] == "d"  # unverändert gemerged


def test_scene_dialoge_und_musik():
    s = screenplay.create_scene(PROJECT_ID, {
        "title": "Dialog",
        "character_ids": ["a" * 32],
        "dialogues": [{"character_id": "a" * 32, "line": "Ich bin zu spät.", "emotion": "resigniert"}],
        "music": {"enabled": True, "prompt": "melancholisches Cello"},
        "camera": {"shot": "wide", "mood": "somber", "unbekannt": "wird verworfen"},
    })
    assert s["dialogues"][0]["line"] == "Ich bin zu spät."
    assert s["music"]["enabled"] is True
    assert s["camera"]["shot"] == "wide"
    assert "unbekannt" not in s["camera"]


def test_scene_delete_raeumt_order():
    s = screenplay.create_scene(PROJECT_ID, {"title": "weg"})
    assert screenplay.delete_scene(PROJECT_ID, s["id"]) is True
    sp = screenplay.get_screenplay(PROJECT_ID)
    assert s["id"] not in sp["scene_order"]
    assert screenplay.get_scene(PROJECT_ID, s["id"]) is None


def test_scene_ungueltige_id():
    assert screenplay.get_scene(PROJECT_ID, "keine-hex-id") is None
    assert screenplay.delete_scene(PROJECT_ID, "keine-hex-id") is False


# ----------------------------------------------------------------- Task 4: Reorder
def test_reorder_permutation():
    a = screenplay.create_scene(PROJECT_ID, {"title": "A"})
    b = screenplay.create_scene(PROJECT_ID, {"title": "B"})
    c = screenplay.create_scene(PROJECT_ID, {"title": "C"})
    screenplay.reorder_scenes(PROJECT_ID, [c["id"], a["id"], b["id"]])
    ids = [s["id"] for s in screenplay.list_scenes(PROJECT_ID)]
    assert ids == [c["id"], a["id"], b["id"]]


def test_reorder_ignoriert_unbekannt_und_ergaenzt_fehlende():
    a = screenplay.create_scene(PROJECT_ID, {"title": "A"})
    b = screenplay.create_scene(PROJECT_ID, {"title": "B"})
    # Client schickt nur b + eine Geister-ID → a fehlt, Geist wird ignoriert
    screenplay.reorder_scenes(PROJECT_ID, [b["id"], "f" * 32])
    ids = [s["id"] for s in screenplay.list_scenes(PROJECT_ID)]
    assert set(ids) == {a["id"], b["id"]}
    assert ids[0] == b["id"]          # bekannte Order zuerst
    assert "f" * 32 not in ids        # Geist raus


# ----------------------------------------------------------------- Task 5: Routen
def test_routen_brauchen_auth(client):
    assert client.get(f"{PREFIX}/screenplay").status_code == 401


def test_routen_fremdes_projekt_404(client, auth_headers):
    assert client.get(f"{OTHER_PREFIX}/screenplay", headers=auth_headers).status_code == 404


def test_route_screenplay_get_put(client, auth_headers):
    assert client.get(f"{PREFIX}/screenplay", headers=auth_headers).json()["title"] == ""
    r = client.put(f"{PREFIX}/screenplay", json={"title": "Film", "film_model": "google/veo-3.1"}, headers=auth_headers)
    assert r.status_code == 200 and r.json()["title"] == "Film"


def test_route_scene_lifecycle(client, auth_headers):
    r = client.post(f"{PREFIX}/screenplay/scenes", json={"title": "S1", "description": "d"}, headers=auth_headers)
    assert r.status_code == 200
    sid = r.json()["id"]
    assert any(s["id"] == sid for s in client.get(f"{PREFIX}/screenplay/scenes", headers=auth_headers).json())
    upd = client.put(f"{PREFIX}/screenplay/scenes/{sid}", json={"title": "S1b"}, headers=auth_headers)
    assert upd.json()["title"] == "S1b"
    assert client.delete(f"{PREFIX}/screenplay/scenes/{sid}", headers=auth_headers).status_code == 200
    assert all(s["id"] != sid for s in client.get(f"{PREFIX}/screenplay/scenes", headers=auth_headers).json())


def test_route_reorder(client, auth_headers):
    a = client.post(f"{PREFIX}/screenplay/scenes", json={"title": "A"}, headers=auth_headers).json()["id"]
    b = client.post(f"{PREFIX}/screenplay/scenes", json={"title": "B"}, headers=auth_headers).json()["id"]
    r = client.post(f"{PREFIX}/screenplay/scenes/reorder", json={"scene_ids": [b, a]}, headers=auth_headers)
    assert r.status_code == 200
    ids = [s["id"] for s in client.get(f"{PREFIX}/screenplay/scenes", headers=auth_headers).json()]
    assert ids == [b, a]
