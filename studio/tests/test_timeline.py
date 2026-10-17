"""Studio 4a: Schnittfassung laden/speichern/prüfen und aus dem Drehbuch übernehmen (studio/SPEC.md „Bauplan Etappe 4“)."""
from __future__ import annotations

import json

from _gen_helpers import PNG
from conftest import MOD_PREFIX, PROJECT_ID

T = f"{MOD_PREFIX}/projects/{PROJECT_ID}/timeline"
P = f"{MOD_PREFIX}/projects/{PROJECT_ID}/plan"
MP4 = b"\x00\x00\x00\x18ftypmp42" + b"\0" * 64


def _media(ws, sub: str, name: str, data: bytes, meta: dict | None = None) -> str:
    d = ws / "studio/media" / sub
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_bytes(data)
    if meta is not None:
        (d / f"{name}.json").write_text(json.dumps(meta))
    return f"studio/media/{sub}/{name}"


def _clip(**kw) -> dict:
    return {"id": "a" * 32, "kind": "image", "start": 0, "in": 0, "out": 5, "media_rel": "", "scene_id": "",
            "shot_id": "", "label": "x", **kw}


def _put(client, h, clips: list[dict], revision: int = 0, **extra):
    return client.put(T, headers=h, json={"revision": revision, "fps": 25,
                                         "tracks": [{"id": "V1", "kind": "video", "clips": clips}], **extra})


def _code(r) -> str:
    return f"{r.status_code} {r.json().get('detail', {}).get('code')}"


def test_empty_timeline_without_creating_anything(client, auth_headers, ws) -> None:
    r = client.get(T, headers=auth_headers)
    assert r.status_code == 200, r.text
    tl = r.json()
    assert tl["revision"] == 0 and tl["fps"] == 25
    assert tl["tracks"] == [{"id": "V1", "kind": "video", "clips": []}]
    assert not (ws / "studio").exists()                                  # Lesen legt nichts an


def test_save_and_load(client, auth_headers, ws) -> None:
    img = _media(ws, "images", "a.png", PNG)
    vid = _media(ws, "videos", "b.mp4", MP4, {"duration": 4})
    clips = [
        _clip(id="1" * 32, kind="video", start=0, out=4, media_rel=vid, label="Hafen · Shot 1", shot_id="2" * 32, scene_id="3" * 32),
        _clip(id="4" * 32, kind="image", start=4, out=6.5, media_rel=img, extra="weg"),
        _clip(id="5" * 32, kind="placeholder", start=10.5, out=3, label="Sturm"),
    ]
    r = _put(client, auth_headers, clips, unknown=1)
    assert r.status_code == 200, r.text
    saved = r.json()
    assert saved["revision"] == 1 and "unknown" not in saved
    got = client.get(T, headers=auth_headers).json()
    assert got == saved
    c = got["tracks"][0]["clips"]
    assert [x["id"] for x in c] == ["1" * 32, "4" * 32, "5" * 32]
    assert c[0] == {"id": "1" * 32, "kind": "video", "start": 0, "in": 0, "out": 4, "media_rel": vid,
                    "scene_id": "3" * 32, "shot_id": "2" * 32, "label": "Hafen · Shot 1"}
    assert "extra" not in c[1] and c[1]["out"] == 6.5
    assert c[2]["media_rel"] == "" and c[2]["start"] == 10.5
    assert (ws / "studio/timelines/main.json").is_file()


def test_ids_labels_and_fps_are_cleaned(client, auth_headers, ws) -> None:
    r = _put(client, auth_headers, [_clip(id="nicht-gültig", kind="placeholder", label="L" * 500, shot_id="../x")], fps=999)
    assert r.status_code == 200, r.text
    c = r.json()["tracks"][0]["clips"][0]
    assert len(c["id"]) == 32 and c["id"] != "nicht-gültig"                # neue gültige ID
    assert len(c["label"]) == 200 and c["shot_id"] == ""
    assert r.json()["fps"] == 25                                         # nur 24/25/30


def test_revision_conflict(client, auth_headers, ws) -> None:
    assert _put(client, auth_headers, [], 0).json()["revision"] == 1
    r = _put(client, auth_headers, [], 0)                                # anderer Tab mit altem Stand
    assert _code(r) == "409 studio_timeline_conflict"
    assert _put(client, auth_headers, [], 1).json()["revision"] == 2


def test_each_rule_rejects_the_whole_timeline(client, auth_headers, ws, tmp_path) -> None:
    img = _media(ws, "images", "a.png", PNG)
    vid = _media(ws, "videos", "b.mp4", MP4)
    outside = tmp_path / "x.png"
    outside.write_bytes(PNG)
    (ws / "studio/media/images/link.png").symlink_to(outside)
    bad = {
        "Pfad mit ..": _clip(media_rel="../x.png"),
        "absoluter Pfad": _clip(media_rel=str(outside)),
        "Symlink": _clip(media_rel="studio/media/images/link.png"),
        "fehlt": _clip(media_rel="studio/media/images/fehlt.png"),
        "falsche Endung": _clip(kind="video", media_rel=img),
        "Bild ohne Medium": _clip(kind="image", media_rel=""),
        "Platzhalter mit Medium": _clip(kind="placeholder", media_rel=img),
        "unbekannte Art": _clip(kind="audio", media_rel=img),
        "Start negativ": _clip(media_rel=img, start=-1),
        "in negativ": _clip(kind="video", media_rel=vid, **{"in": -1}),
        "in = out": _clip(media_rel=img, **{"in": 2, "out": 2}),
        "Text statt Zahl": _clip(media_rel=img, start="1"),
        "unendlich": _clip(media_rel=img, out=float("inf")),
        "über 4 Stunden": _clip(media_rel=img, start=4 * 3600 - 1, out=2),
    }
    for name, clip in bad.items():
        r = _put(client, auth_headers, [clip])
        assert _code(r) == "400 studio_timeline_invalid", name
    too_many = [_clip(id=f"{i:032x}", media_rel=img, start=i, out=1) for i in range(2001)]
    assert _code(_put(client, auth_headers, too_many)) == "400 studio_timeline_invalid"
    assert _code(client.put(T, headers=auth_headers, json={"revision": 0, "tracks": "x"})) == "400 studio_timeline_invalid"
    assert not (ws / "studio/timelines/main.json").exists()               # nichts gespeichert
    assert _put(client, auth_headers, [_clip(media_rel=img, start=4 * 3600 - 2, out=2)]).status_code == 200   # genau 4 h geht


def _shots(client, h, ws, layout: list[list[dict]]) -> list[dict]:
    """Szenen mit Shots anlegen; image_rel/video_rel wie nach dem Erzeugen direkt in die Szenen-Datei schreiben."""
    out = []
    for n, shots in enumerate(layout, start=1):
        sc = client.post(f"{P}/scenes", headers=h, json={"title": f"Szene {n}"}).json()
        for s in shots:
            client.post(f"{P}/scenes/{sc['id']}/shots", headers=h, json={"prompt": s.get("prompt", ""), "duration": s["duration"]})
        f = ws / "studio/scenes" / f"{sc['id']}.json"
        data = json.loads(f.read_text())
        for raw, s in zip(data["shots"], shots):
            raw["image_rel"], raw["video_rel"] = s.get("image"), s.get("video")
        f.write_text(json.dumps(data))
        out.append({**sc, "shots": data["shots"]})
    return out


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


def test_broken_file_reads_as_empty(client, auth_headers, ws) -> None:
    (ws / "studio/timelines").mkdir(parents=True)
    (ws / "studio/timelines/main.json").write_text("{kaputt")
    tl = client.get(T, headers=auth_headers).json()
    assert tl["revision"] == 0 and tl["tracks"][0]["clips"] == []


def test_only_members(client, other_headers, ws) -> None:
    assert _code(client.get(T, headers=other_headers)) == "404 studio_project_not_found"
    assert _code(client.put(T, headers=other_headers, json={"revision": 0, "tracks": []})) == "404 studio_project_not_found"
    assert _code(client.post(f"{T}/from-plan", headers=other_headers, json={})) == "404 studio_project_not_found"
