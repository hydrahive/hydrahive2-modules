"""Studio Etappe 2a: Planungsdaten aus dem Atelier übernehmen – als Kopie, Atelier bleibt unangetastet."""
from __future__ import annotations

import json
from pathlib import Path

from conftest import MOD_PREFIX, PROJECT_ID

P = f"{MOD_PREFIX}/projects/{PROJECT_ID}/plan"
SC = "a" * 32
SC2 = "b" * 32
CH = "c" * 32


def _atelier(ws: Path) -> None:
    a = ws / "atelier"
    (a / "screenplay/scenes").mkdir(parents=True, exist_ok=True)
    (a / "screenplay/shots").mkdir(parents=True, exist_ok=True)
    (a / f"characters/{CH}").mkdir(parents=True, exist_ok=True)
    (a / "screenplay/screenplay.json").write_text(json.dumps({
        "title": "Nordwind", "logline": "Sturm am Hafen", "film_model": "kling", "audio_model": "lyria", "voice_model": "",
        "aspect_ratio": "16:9", "default_duration": 6, "scene_order": [SC2, SC]}))
    (a / f"screenplay/scenes/{SC}.json").write_text(json.dumps({
        "id": SC, "title": "Hafen", "character_ids": [CH], "camera": {"shot": "wide"},
        "dialogues": [{"character_id": CH, "line": "Wo bist du?", "emotion": "leise"}]}))
    (a / f"screenplay/scenes/{SC2}.json").write_text(json.dumps({"id": SC2, "title": "Vorspann"}))
    (a / f"screenplay/shots/{SC}.json").write_text(json.dumps([
        {"id": "1" * 32, "scene_id": SC, "order": 0, "shot": "wide", "prompt": "harbor at dawn", "character_ids": [CH],
         "duration": 5, "status": "done", "video_rel": "videos/x.mp4"}]))
    (a / f"characters/{CH}/character.json").write_text(json.dumps({
        "id": CH, "name": "Mira", "description": "rote Haare", "references": [f"characters/{CH}/a.png"]}))
    (a / f"characters/{CH}/a.png").write_bytes(b"png")
    (a / "ci.json").write_text(json.dumps({"style_anchor": "ink wash", "palette": ["#123456"]}))


def _snapshot(root: Path) -> dict[str, bytes]:
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def test_preview_counts_without_writing(client, auth_headers, ws) -> None:
    _atelier(ws)
    r = client.get(f"{P}/import/atelier", headers=auth_headers)
    assert r.status_code == 200, r.text
    assert r.json() == {"available": True, "scenes": 2, "shots": 1, "elements": 1, "look": True, "plan_exists": False}
    assert not (ws / "studio").exists()


def test_import_copies_and_leaves_atelier_alone(client, auth_headers, ws) -> None:
    _atelier(ws)
    before = _snapshot(ws / "atelier")

    r = client.post(f"{P}/import/atelier", headers=auth_headers)

    assert r.status_code == 200, r.text
    assert r.json()["scenes"] == 2 and r.json()["shots"] == 1 and r.json()["elements"] == 1
    assert _snapshot(ws / "atelier") == before                        # Atelier unverändert
    plan = client.get(P, headers=auth_headers).json()
    head = plan["screenplay"]
    assert head["title"] == "Nordwind" and head["default_duration"] == 6
    assert head["models"]["video"] == "kling" and head["models"]["music"] == "lyria"
    assert head["look"] == {"style": "ink wash", "palette": ["#123456"]}
    assert [s["id"] for s in plan["scenes"]] == [SC2, SC]              # Reihenfolge bleibt
    hafen = plan["scenes"][1]
    assert hafen["element_ids"] == [CH] and hafen["dialogues"][0]["element_id"] == CH
    assert hafen["shots"][0]["prompt"] == "harbor at dawn" and hafen["shots"][0]["element_ids"] == [CH]
    assert hafen["shots"][0]["status"] == "done" and hafen["shots"][0]["video_rel"] == "atelier/videos/x.mp4"
    mira = plan["elements"][0]
    assert mira["kind"] == "character" and mira["name"] == "Mira" and mira["references"] == [f"atelier/characters/{CH}/a.png"]
    meta = json.loads((ws / "studio/imported.json").read_text())
    assert meta["source"] == "atelier" and meta["scenes"] == 2


def test_import_never_overwrites(client, auth_headers, ws) -> None:
    _atelier(ws)
    client.post(f"{P}/scenes", headers=auth_headers, json={"title": "schon da"})
    r = client.post(f"{P}/import/atelier", headers=auth_headers)
    assert r.status_code == 409 and r.json()["detail"]["code"] == "studio_plan_exists"
    assert [s["title"] for s in client.get(P, headers=auth_headers).json()["scenes"]] == ["schon da"]
    assert client.get(f"{P}/import/atelier", headers=auth_headers).json()["plan_exists"] is True


def test_nothing_to_import(client, auth_headers, ws) -> None:
    assert client.get(f"{P}/import/atelier", headers=auth_headers).json()["available"] is False
    r = client.post(f"{P}/import/atelier", headers=auth_headers)
    assert r.status_code == 404 and r.json()["detail"]["code"] == "studio_nothing_to_import"
    assert not (ws / "studio").exists()


def test_broken_atelier_files_are_skipped(client, auth_headers, ws) -> None:
    _atelier(ws)
    (ws / f"atelier/screenplay/scenes/{'d' * 32}.json").write_text("{kaputt")
    (ws / "atelier/screenplay/scenes/nicht-hex.json").write_text(json.dumps({"id": "nicht-hex", "title": "x"}))
    (ws / f"atelier/screenplay/shots/{SC2}.json").write_text("kaputt")
    r = client.post(f"{P}/import/atelier", headers=auth_headers)
    assert r.status_code == 200 and r.json()["scenes"] == 2
    assert client.get(P, headers=auth_headers).json()["scenes"][0]["shots"] == []
