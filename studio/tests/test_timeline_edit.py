"""Studio 4b: magnetische Hauptspur – keine Überlappungen auf V1 (studio/SPEC.md „Bauplan 4b“)."""
from __future__ import annotations

import json

from _gen_helpers import PNG
from _timeline_helpers import T, _clip, _code, _media, _put


def test_overlap_rejects_whole_timeline(client, auth_headers, ws) -> None:
    img = _media(ws, "images", "a.png", PNG)
    a = _clip(id="1" * 32, media_rel=img, start=0, out=5)
    for name, b in {
        "beginnt mitten im ersten": _clip(id="2" * 32, media_rel=img, start=4.9, out=2),
        "liegt ganz darin": _clip(id="2" * 32, media_rel=img, start=1, out=1),
        "gleicher Start": _clip(id="2" * 32, media_rel=img, start=0, out=1),
    }.items():
        assert _code(_put(client, auth_headers, [a, b])) == "400 studio_timeline_invalid", name
        assert _code(_put(client, auth_headers, [b, a])) == "400 studio_timeline_invalid", f"{name} (andere Reihenfolge)"
    assert not (ws / "studio/timelines/main.json").exists()


def test_touching_and_gaps_are_fine(client, auth_headers, ws) -> None:
    img = _media(ws, "images", "a.png", PNG)
    clips = [_clip(id="1" * 32, media_rel=img, start=0, out=5),
             _clip(id="2" * 32, media_rel=img, start=5, out=2),          # stößt genau an
             _clip(id="3" * 32, media_rel=img, start=9, out=1)]          # Lücke 7–9 (ältere Daten)
    r = _put(client, auth_headers, list(reversed(clips)))
    assert r.status_code == 200, r.text
    got = r.json()["tracks"][0]["clips"]
    assert [c["id"] for c in got] == ["1" * 32, "2" * 32, "3" * 32]       # nach Start sortiert
    near = [_clip(id="1" * 32, media_rel=img, start=0, out=0.12),         # Rundung: 3 Bilder bei 25 fps
            _clip(id="2" * 32, media_rel=img, start=0.12, out=1)]
    assert _put(client, auth_headers, near, 1).status_code == 200
    eps = [_clip(id="1" * 32, media_rel=img, start=0, out=1.0000004), _clip(id="2" * 32, media_rel=img, start=1, out=1)]
    assert _put(client, auth_headers, eps, 2).status_code == 200          # winzige Gleitkomma-Reste zählen nicht


def test_overlapping_clip_in_file_is_skipped_on_load(client, auth_headers, ws) -> None:
    img = _media(ws, "images", "a.png", PNG)
    (ws / "studio/timelines").mkdir(parents=True)
    (ws / "studio/timelines/main.json").write_text(json.dumps({"revision": 3, "fps": 25, "tracks": [{"id": "V1", "clips": [
        _clip(id="1" * 32, media_rel=img, start=0, out=5), _clip(id="2" * 32, media_rel=img, start=3, out=4),
        _clip(id="3" * 32, media_rel=img, start=5, out=2)]}]}))
    tl = client.get(T, headers=auth_headers).json()
    assert [c["id"] for c in tl["tracks"][0]["clips"]] == ["1" * 32, "3" * 32]
    assert _put(client, auth_headers, tl["tracks"][0]["clips"], 3).status_code == 200   # so wieder speicherbar
