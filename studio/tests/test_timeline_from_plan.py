"""Studio 4a: Schnittfassung aus dem Drehbuch übernehmen (studio/SPEC.md „Bauplan Etappe 4“)."""
from __future__ import annotations

from _gen_helpers import PNG
from _timeline_helpers import MP4, P, T, _code, _media, _shots


def test_from_plan_builds_v1_in_screenplay_order(client, auth_headers, ws) -> None:
    img = _media(ws, "images", "a.png", PNG)
    vid = _media(ws, "videos", "b.mp4", MP4, {"duration": 4})
    vid_nometa = _media(ws, "videos", "c.mp4", MP4)
    sc = _shots(client, auth_headers, ws, [
        [{"duration": 7, "image": img, "video": vid}, {"duration": 3, "image": img}, {"duration": 5, "prompt": "Boot legt an"}],
        [{"duration": 6, "image": img, "video": vid_nometa}, {"duration": 2, "image": img, "video": "studio/media/videos/weg.mp4"},
         {"duration": 4, "video": "studio/media/videos/weg.mp4"}],
    ])
    r = client.post(f"{T}/from-plan", headers=auth_headers, json={})
    assert r.status_code == 200, r.text
    clips = r.json()["tracks"][0]["clips"]
    assert [(c["kind"], c["start"], c["in"], c["out"], c["media_rel"]) for c in clips] == [
        ("video", 0, 0, 4, vid),                    # Länge aus der Begleitdatei des Videos
        ("image", 4, 0, 3, img),                    # Standbild mit Shot-Dauer
        ("placeholder", 7, 0, 5, ""),
        ("video", 12, 0, 6, vid_nometa),            # ohne Begleitdatei: Shot-Dauer
        ("image", 18, 0, 2, img),                   # Video fehlt → Standbild
        ("placeholder", 20, 0, 4, ""),              # Video fehlt, kein Bild → Platzhalter
    ]
    assert [c["shot_id"] for c in clips] == [s["id"] for x in sc for s in x["shots"]]
    assert [c["scene_id"] for c in clips] == [sc[0]["id"]] * 3 + [sc[1]["id"]] * 3
    assert [c["label"] for c in clips][:3] == ["Szene 1 · Shot 1", "Szene 1 · Shot 2", "Szene 1 · Shot 3"]
    assert len({c["id"] for c in clips}) == 6
    assert r.json()["revision"] == 1
    assert client.get(T, headers=auth_headers).json() == r.json()


def test_from_plan_asks_before_replacing(client, auth_headers, ws) -> None:
    _shots(client, auth_headers, ws, [[{"duration": 3}]])
    assert client.post(f"{T}/from-plan", headers=auth_headers, json={}).status_code == 200
    r = client.post(f"{T}/from-plan", headers=auth_headers, json={})
    assert _code(r) == "409 studio_timeline_not_empty"
    assert client.get(T, headers=auth_headers).json()["revision"] == 1      # unverändert
    r = client.post(f"{T}/from-plan", headers=auth_headers, json={"replace": True})
    assert r.status_code == 200 and r.json()["revision"] == 2
    assert client.post(f"{T}/from-plan", headers=auth_headers, json={"replace": "ja"}).status_code == 409   # nur echtes true


def test_from_plan_without_shots(client, auth_headers, ws) -> None:
    assert _code(client.post(f"{T}/from-plan", headers=auth_headers, json={})) == "400 studio_timeline_no_shots"
    client.post(f"{P}/scenes", headers=auth_headers, json={"title": "leer"})
    assert _code(client.post(f"{T}/from-plan", headers=auth_headers, json={})) == "400 studio_timeline_no_shots"
