"""Studio 2b: Shots einer Szene bearbeiten (studio/SPEC.md „Bauplan 2b“)."""
from __future__ import annotations

from conftest import MOD_PREFIX, OTHER_PROJECT_ID, PROJECT_ID

P = f"{MOD_PREFIX}/projects/{PROJECT_ID}/plan"


def _scene(client, h, **extra) -> dict:
    return client.post(f"{P}/scenes", headers=h, json={"title": "Hafen", **extra}).json()


def test_add_update_delete_shot(client, auth_headers, ws) -> None:
    client.put(f"{P}/screenplay", headers=auth_headers, json={"default_duration": 7})
    mira = client.post(f"{P}/elements", headers=auth_headers, json={"kind": "character", "name": "Mira"}).json()
    ole = client.post(f"{P}/elements", headers=auth_headers, json={"kind": "character", "name": "Ole"}).json()
    sc = _scene(client, auth_headers, element_ids=[mira["id"]])
    S = f"{P}/scenes/{sc['id']}/shots"

    r = client.post(S, headers=auth_headers, json={})
    assert r.status_code == 200, r.text
    a = r.json()
    assert a["duration"] == 7 and a["status"] == "planned" and a["order"] == 0     # Standarddauer aus dem Kopf
    b = client.post(S, headers=auth_headers, json={"prompt": "Boot", "duration": 3}).json()
    assert b["order"] == 1 and b["prompt"] == "Boot" and b["duration"] == 3

    up = client.put(f"{S}/{a['id']}", headers=auth_headers, json={
        "shot": "closeup", "prompt": "x" * 3000, "duration": 99, "element_ids": [mira["id"], ole["id"]],
        "status": "done", "image_rel": "../../etc/passwd", "video_rel": "a.mp4", "order": 9})
    assert up.status_code == 200, up.text
    s = up.json()
    assert s["shot"] == "closeup" and len(s["prompt"]) == 2000 and s["duration"] == 60
    assert s["element_ids"] == [mira["id"]]                                # nur Bausteine der Szene
    assert s["status"] == "planned" and s["image_rel"] is None and s["video_rel"] is None   # nur das Erzeugen ändert das
    assert s["order"] == 0
    assert client.put(f"{S}/{a['id']}", headers=auth_headers, json={"shot": "erfunden"}).json()["shot"] == ""

    plan = client.get(P, headers=auth_headers).json()
    assert [x["id"] for x in plan["scenes"][0]["shots"]] == [a["id"], b["id"]]
    assert plan["scenes"][0]["title"] == "Hafen"                           # Szene bleibt sonst unverändert

    assert client.delete(f"{S}/{a['id']}", headers=auth_headers).status_code == 200
    left = client.get(P, headers=auth_headers).json()["scenes"][0]["shots"]
    assert [x["id"] for x in left] == [b["id"]] and left[0]["order"] == 0
    assert client.delete(f"{S}/{a['id']}", headers=auth_headers).status_code == 404
    assert client.put(f"{S}/{a['id']}", headers=auth_headers, json={}).status_code == 404


def test_reorder_shots(client, auth_headers, ws) -> None:
    sc = _scene(client, auth_headers)
    S = f"{P}/scenes/{sc['id']}/shots"
    ids = [client.post(S, headers=auth_headers, json={"prompt": str(i)}).json()["id"] for i in range(3)]
    r = client.put(f"{S}/order", headers=auth_headers, json={"shot_ids": [ids[2], "f" * 32, ids[0]]})
    assert r.status_code == 200, r.text
    got = r.json()["shots"]
    assert [x["id"] for x in got] == [ids[2], ids[0], ids[1]]               # unbekannte weg, fehlende hinten an
    assert [x["order"] for x in got] == [0, 1, 2]
    assert [x["prompt"] for x in client.get(P, headers=auth_headers).json()["scenes"][0]["shots"]] == ["2", "0", "1"]


def test_shot_ids_and_members_are_checked(client, auth_headers, other_headers, ws) -> None:
    sc = _scene(client, auth_headers)
    S = f"{P}/scenes/{sc['id']}/shots"
    assert client.post(f"{P}/scenes/{'a' * 32}/shots", headers=auth_headers, json={}).status_code == 404
    assert client.post(f"{P}/scenes/..%2Fx/shots", headers=auth_headers, json={}).status_code == 404
    assert client.put(f"{S}/nicht-hex", headers=auth_headers, json={}).status_code == 404
    assert client.post(S, headers=other_headers, json={}).status_code == 404
    assert client.post(f"{MOD_PREFIX}/projects/{OTHER_PROJECT_ID}/plan/scenes/{sc['id']}/shots", headers=auth_headers, json={}).status_code == 404
    assert client.post(S, json={}).status_code == 401


def test_at_most_50_shots(client, auth_headers, ws) -> None:
    sc = _scene(client, auth_headers)
    S = f"{P}/scenes/{sc['id']}/shots"
    for _ in range(50):
        assert client.post(S, headers=auth_headers, json={}).status_code == 200
    r = client.post(S, headers=auth_headers, json={})
    assert r.status_code == 400 and r.json()["detail"]["code"] == "studio_too_many_shots"
