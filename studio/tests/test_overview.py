"""Studio B1: Übersicht je Projekt für Start-Reiter und Fortschritt (studio/SPEC.md „Etappe B“)."""
from __future__ import annotations

import json

from _gen_helpers import PNG
from _timeline_helpers import MP4, _media, _shots
from conftest import MOD_PREFIX, PROJECT_ID

O = f"{MOD_PREFIX}/projects/{PROJECT_ID}/overview"


def test_empty_project_without_creating_anything(client, auth_headers, ws) -> None:
    r = client.get(O, headers=auth_headers)
    assert r.status_code == 200, r.text
    assert r.json() == {"scenes": 0, "shots": 0, "with_image": 0, "with_video": 0, "clips": 0, "atelier": False}
    assert not (ws / "studio").exists()


def test_counts(client, auth_headers, ws) -> None:
    img = _media(ws, "images", "a.png", PNG)
    vid = _media(ws, "videos", "b.mp4", MP4, {"duration": 4})
    _shots(client, auth_headers, ws, [
        [{"duration": 3, "image": img, "video": vid}, {"duration": 3, "image": img}, {"duration": 3}],
        [],
    ])
    client.post(f"{MOD_PREFIX}/projects/{PROJECT_ID}/timeline/from-plan", headers=auth_headers, json={})
    o = client.get(O, headers=auth_headers).json()
    assert o == {"scenes": 2, "shots": 3, "with_image": 2, "with_video": 1, "clips": 3, "atelier": False}


def test_atelier_offer(client, auth_headers, ws) -> None:
    d = ws / "atelier/screenplay/scenes"
    d.mkdir(parents=True)
    (d / f"{'1' * 32}.json").write_text(json.dumps({"title": "Alt"}))
    assert client.get(O, headers=auth_headers).json()["atelier"] is True
    client.post(f"{MOD_PREFIX}/projects/{PROJECT_ID}/plan/scenes", headers=auth_headers, json={"title": "Neu"})
    assert client.get(O, headers=auth_headers).json()["atelier"] is False      # Studio hat schon eine Planung


def test_only_members(client, other_headers, ws) -> None:
    r = client.get(O, headers=other_headers)
    assert r.status_code == 404 and r.json()["detail"]["code"] == "studio_project_not_found"
