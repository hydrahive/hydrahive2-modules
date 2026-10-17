"""Studio Etappe 2a: Planungsdaten im eigenen studio/-Ordner (studio/SPEC.md „Bauplan Etappe 2“)."""
from __future__ import annotations

import json

from conftest import MOD_PREFIX, OTHER_PROJECT_ID, PROJECT_ID

P = f"{MOD_PREFIX}/projects/{PROJECT_ID}/plan"


def test_empty_plan_without_creating_anything(client, auth_headers, ws) -> None:
    r = client.get(P, headers=auth_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["screenplay"]["title"] == "" and body["screenplay"]["scene_order"] == []
    assert body["scenes"] == [] and body["elements"] == []
    assert body["presets"]["shot"][:3] == ["extreme_closeup", "closeup", "medium"]
    assert not (ws / "studio").exists()                                # Lesen legt nichts an


def test_head_is_cleaned_and_saved_atomically(client, auth_headers, ws) -> None:
    r = client.put(f"{P}/screenplay", headers=auth_headers, json={
        "title": "T" * 500, "logline": "Ein Sturm", "aspect_ratio": "9:16", "default_duration": 999,
        "models": {"video": "kling", "evil": "x"}, "look": {"style": "noir", "palette": ["#111"] * 20}, "scene_order": ["../x"]})
    assert r.status_code == 200, r.text
    head = r.json()
    assert len(head["title"]) == 200 and head["default_duration"] == 60 and head["aspect_ratio"] == "9:16"
    assert head["models"] == {"video": "kling", "image": "", "voice": "", "music": "", "text": ""}
    assert len(head["look"]["palette"]) == 12 and head["scene_order"] == []
    f = ws / "studio" / "screenplay.json"
    assert json.loads(f.read_text())["logline"] == "Ein Sturm"
    assert not list((ws / "studio").glob("*.tmp"))


def test_scenes_crud_and_order(client, auth_headers, ws) -> None:
    el = client.post(f"{P}/elements", headers=auth_headers, json={"kind": "character", "name": "Mira"}).json()
    a = client.post(f"{P}/scenes", headers=auth_headers, json={
        "title": "Hafen", "location": "Steg", "time_of_day": "dawn", "element_ids": [el["id"], "fremd"],
        "dialogues": [{"element_id": el["id"], "line": "Wo bist du?", "emotion": "leise"}, {"line": ""}],
        "camera": {"shot": "wide", "light": "golden_hour", "erfunden": "x"}}).json()
    b = client.post(f"{P}/scenes", headers=auth_headers, json={"title": "Sturm"}).json()
    assert a["element_ids"] == [el["id"]]                              # nur vorhandene Bausteine
    assert a["dialogues"] == [{"element_id": el["id"], "line": "Wo bist du?", "emotion": "leise"}]
    assert a["camera"] == {"shot": "wide", "light": "golden_hour"} and a["shots"] == []
    plan = client.get(P, headers=auth_headers).json()
    assert [s["id"] for s in plan["scenes"]] == [a["id"], b["id"]]

    r = client.put(f"{P}/order", headers=auth_headers, json={"scene_order": [b["id"], a["id"], "gibt-es-nicht"]})
    assert r.status_code == 200 and r.json()["scene_order"] == [b["id"], a["id"]]
    assert [s["id"] for s in client.get(P, headers=auth_headers).json()["scenes"]] == [b["id"], a["id"]]

    up = client.put(f"{P}/scenes/{a['id']}", headers=auth_headers, json={"title": "Hafen am Morgen", "description": "x" * 5000})
    assert up.status_code == 200 and up.json()["title"] == "Hafen am Morgen" and len(up.json()["description"]) == 4000
    assert client.delete(f"{P}/scenes/{b['id']}", headers=auth_headers).status_code == 200
    plan = client.get(P, headers=auth_headers).json()
    assert [s["id"] for s in plan["scenes"]] == [a["id"]] and plan["screenplay"]["scene_order"] == [a["id"]]
    assert client.put(f"{P}/scenes/{b['id']}", headers=auth_headers, json={}).status_code == 404


def test_elements_with_references_from_the_library(client, auth_headers, ws, setup_test_env) -> None:
    (ws / "atelier/images").mkdir(parents=True, exist_ok=True)
    (ws / "atelier/images/mira.png").write_bytes(b"png")
    (ws / "atelier/images/text.txt").write_text("x")
    outside = setup_test_env / "draussen.png"
    outside.write_bytes(b"png")
    (ws / "atelier/images/link.png").symlink_to(outside)
    el = client.post(f"{P}/elements", headers=auth_headers, json={
        "kind": "place", "name": "Hafen", "description": "Alter Fischerhafen",
        "references": ["atelier/images/mira.png", "atelier/images/text.txt", "atelier/images/link.png", "../../etc/passwd", "/abs.png"]}).json()
    assert el["kind"] == "place" and el["references"] == ["atelier/images/mira.png"]
    assert (ws / "studio" / "elements" / el["id"] / "element.json").is_file()
    bad = client.post(f"{P}/elements", headers=auth_headers, json={"kind": "drache", "name": "x"})
    assert bad.status_code == 400 and bad.json()["detail"]["code"] == "studio_element_invalid"
    assert client.post(f"{P}/elements", headers=auth_headers, json={"kind": "object", "name": "  "}).status_code == 400

    sc = client.post(f"{P}/scenes", headers=auth_headers, json={"title": "S", "element_ids": [el["id"]],
                     "dialogues": [{"element_id": el["id"], "line": "Hallo"}]}).json()
    assert client.delete(f"{P}/elements/{el['id']}", headers=auth_headers).status_code == 200
    scene = client.get(P, headers=auth_headers).json()["scenes"][0]
    assert scene["id"] == sc["id"] and scene["element_ids"] == []      # Verweis wird entfernt …
    assert scene["dialogues"] == [{"element_id": "", "line": "Hallo", "emotion": ""}]   # … der Dialog bleibt
    assert (ws / "atelier/images/mira.png").is_file()                 # Referenzbild bleibt


def test_ids_are_checked_and_only_members(client, auth_headers, other_headers, ws) -> None:
    assert client.put(f"{P}/scenes/..%2F..%2Fx", headers=auth_headers, json={}).status_code == 404
    assert client.delete(f"{P}/elements/nicht-hex", headers=auth_headers).status_code == 404
    r = client.get(P, headers=other_headers)
    assert r.status_code == 404 and r.json()["detail"]["code"] == "studio_project_not_found"
    assert client.post(f"{P}/scenes", headers=other_headers, json={"title": "x"}).status_code == 404
    assert client.get(f"{MOD_PREFIX}/projects/{OTHER_PROJECT_ID}/plan", headers=auth_headers).status_code == 404
    assert client.get(P).status_code == 401


def test_broken_files_do_not_break_the_plan(client, auth_headers, ws) -> None:
    good = client.post(f"{P}/scenes", headers=auth_headers, json={"title": "gut"}).json()
    (ws / "studio/scenes/ffffffffffffffffffffffffffffffff.json").write_text("{kaputt")
    (ws / "studio/screenplay.json").write_text("[]")
    plan = client.get(P, headers=auth_headers).json()
    assert [s["title"] for s in plan["scenes"]] == ["gut"] and plan["screenplay"]["title"] == ""
    assert good["id"] in [s["id"] for s in plan["scenes"]]           # Szene ohne gültige Reihenfolge erscheint trotzdem
