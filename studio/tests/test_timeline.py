"""Studio 4a: Schnittfassung laden/speichern/prüfen und aus dem Drehbuch übernehmen (studio/SPEC.md „Bauplan Etappe 4“)."""
from __future__ import annotations

import json

from _gen_helpers import PNG
from _timeline_helpers import MP4, T, _clip, _code, _media, _put, _shots


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
        "Wahrheitswert statt Zahl": _clip(media_rel=img, start=True),
        "über 4 Stunden": _clip(media_rel=img, start=4 * 3600 - 1, out=2),
    }
    for name, clip in bad.items():
        r = _put(client, auth_headers, [clip])
        assert _code(r) == "400 studio_timeline_invalid", name
    for field, bad_num in (("out", "1e999"), ("in", "NaN"), ("start", "NaN"), ("out", "NaN")):   # nur als rohes JSON möglich
        raw = json.dumps({"revision": 0, "tracks": [{"clips": [_clip(media_rel=img, **{field: 12345})]}]}).replace("12345", bad_num)
        r = client.put(T, headers={**auth_headers, "Content-Type": "application/json"}, content=raw)
        assert _code(r) == "400 studio_timeline_invalid", f"{field}={bad_num}"
    too_many = [_clip(id=f"{i:032x}", media_rel=img, start=i, out=1) for i in range(2001)]
    assert _code(_put(client, auth_headers, too_many)) == "400 studio_timeline_invalid"
    assert _code(client.put(T, headers=auth_headers, json={"revision": 0, "tracks": "x"})) == "400 studio_timeline_invalid"
    assert not (ws / "studio/timelines/main.json").exists()               # nichts gespeichert
    assert _put(client, auth_headers, [_clip(media_rel=img, start=4 * 3600 - 2, out=2)]).status_code == 200   # genau 4 h geht


def test_broken_file_reads_as_empty(client, auth_headers, ws) -> None:
    (ws / "studio/timelines").mkdir(parents=True)
    (ws / "studio/timelines/main.json").write_text("{kaputt")
    tl = client.get(T, headers=auth_headers).json()
    assert tl["revision"] == 0 and tl["tracks"][0]["clips"] == []


def test_only_members(client, other_headers, ws) -> None:
    assert _code(client.get(T, headers=other_headers)) == "404 studio_project_not_found"
    assert _code(client.put(T, headers=other_headers, json={"revision": 0, "tracks": []})) == "404 studio_project_not_found"
    assert _code(client.post(f"{T}/from-plan", headers=other_headers, json={})) == "404 studio_project_not_found"


def test_deleted_media_becomes_placeholder_and_nothing_else_is_lost(client, auth_headers, ws) -> None:
    img = _media(ws, "images", "a.png", PNG)
    vid = _media(ws, "videos", "b.mp4", MP4)
    r = _put(client, auth_headers, [
        _clip(id="1" * 32, kind="video", media_rel=vid, start=0, out=4, label="Hafen", shot_id="2" * 32),
        _clip(id="3" * 32, media_rel=img, start=4, out=3),
    ])
    assert r.status_code == 200
    (ws / vid).unlink()                                                  # Video später gelöscht
    tl = client.get(T, headers=auth_headers).json()
    assert tl["revision"] == 1
    a, b = tl["tracks"][0]["clips"]
    assert a == {"id": "1" * 32, "kind": "placeholder", "start": 0, "in": 0, "out": 4, "media_rel": "", "scene_id": "",
                 "shot_id": "2" * 32, "label": "Hafen", "missing": True}
    assert b["kind"] == "image" and b["media_rel"] == img and "missing" not in b
    assert _put(client, auth_headers, tl["tracks"][0]["clips"], 1).status_code == 200   # lässt sich so wieder speichern
    assert client.get(T, headers=auth_headers).json()["tracks"][0]["clips"][0]["missing"] is True


def test_single_broken_clip_in_file_is_skipped(client, auth_headers, ws) -> None:
    img = _media(ws, "images", "a.png", PNG)
    (ws / "studio/timelines").mkdir(parents=True)
    good = _clip(id="1" * 32, media_rel=img, out=3)
    (ws / "studio/timelines/main.json").write_text(json.dumps({"revision": 7, "fps": 25, "tracks": [{"id": "V1", "clips": [
        good, {"kind": "video", "start": "x"}, "Unsinn", _clip(id="2" * 32, kind="placeholder", start=3, out=2)]}]}))
    tl = client.get(T, headers=auth_headers).json()
    assert tl["revision"] == 7
    assert [c["id"] for c in tl["tracks"][0]["clips"]] == ["1" * 32, "2" * 32]
    assert all("missing" not in c for c in tl["tracks"][0]["clips"])


def test_answers_carry_the_project_folder_for_files(client, auth_headers, ws) -> None:
    """Wie GET plan: `base` = Projektordner, damit die Oberfläche Bilder/Videos über /api/files zeigen kann."""
    _shots(client, auth_headers, ws, [[{"duration": 3}]])
    for r in (client.get(T, headers=auth_headers), _put(client, auth_headers, []),
              client.post(f"{T}/from-plan", headers=auth_headers, json={"replace": True})):
        assert r.status_code == 200, r.text
        assert r.json()["base"] == str(ws)
    assert "base" not in json.loads((ws / "studio/timelines/main.json").read_text())   # nicht in der Datei


def test_file_values_are_checked_on_load(client, auth_headers, ws) -> None:
    (ws / "studio/timelines").mkdir(parents=True)
    f = ws / "studio/timelines/main.json"
    for raw_rev, raw_fps, want_rev, want_fps in ((-3, 999, 0, 25), ("7", "25", 0, 25), (True, None, 0, 25), (4, 30, 4, 30)):
        f.write_text(json.dumps({"revision": raw_rev, "fps": raw_fps, "tracks": [{"id": "V1", "clips": []}]}))
        tl = client.get(T, headers=auth_headers).json()
        assert (tl["revision"], tl["fps"]) == (want_rev, want_fps), (raw_rev, raw_fps)
