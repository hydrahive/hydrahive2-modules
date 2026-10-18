"""Studio 5a: Tonspuren „Sprache“ (A1) und „Musik“ (A2) in der Schnittfassung (studio/SPEC.md „Bauplan Etappe 5“)."""
from __future__ import annotations

import json

from _gen_helpers import PNG
from _timeline_helpers import T, _aclip, _audio, _clip, _code, _media, _put, _put_tracks

EMPTY_AUDIO = [{"id": "A1", "kind": "audio", "clips": []}, {"id": "A2", "kind": "audio", "clips": []}]


def test_empty_timeline_has_both_audio_tracks(client, auth_headers, ws) -> None:
    tl = client.get(T, headers=auth_headers).json()
    assert tl["tracks"] == [{"id": "V1", "kind": "video", "clips": []}, *EMPTY_AUDIO]
    assert not (ws / "studio").exists()


def test_old_file_without_audio_tracks_gets_them_on_load_unchanged_on_disk(client, auth_headers, ws) -> None:
    img = _media(ws, "images", "a.png", PNG)
    f = ws / "studio/timelines/main.json"
    old = {"revision": 2, "fps": 25, "tracks": [{"id": "V1", "kind": "video", "clips": [_clip(media_rel=img)]}]}
    f.write_text(json.dumps(old))
    tl = client.get(T, headers=auth_headers).json()
    assert [t["id"] for t in tl["tracks"]] == ["V1", "A1", "A2"] and tl["tracks"][1:] == EMPTY_AUDIO
    assert len(tl["tracks"][0]["clips"]) == 1
    assert json.loads(f.read_text()) == old                               # Lesen schreibt nichts
    assert _put(client, auth_headers, tl["tracks"][0]["clips"], 2).status_code == 200   # alter Client (nur V1) geht weiter


def test_save_and_load_audio_clips(client, auth_headers, ws) -> None:
    img = _media(ws, "images", "a.png", PNG)
    m = _audio(ws, "lied.mp3", {"duration": 30})
    s = _audio(ws, "satz.wav", sub="tonstudio/clips")
    voice = [_aclip(id="1" * 32, start=1, out=2.5, media_rel=s, label="Satz", extra="weg")]
    music = [_aclip(id="2" * 32, start=0, out=8, media_rel=m), _aclip(id="3" * 32, start=10, **{"in": 3, "out": 9}, media_rel=m)]
    r = _put_tracks(client, auth_headers, [_clip(media_rel=img, out=4)], voice, music)
    assert r.status_code == 200, r.text
    got = client.get(T, headers=auth_headers).json()
    assert got == r.json()
    a1, a2 = got["tracks"][1]["clips"], got["tracks"][2]["clips"]
    assert a1 == [{"id": "1" * 32, "kind": "audio", "start": 1, "in": 0, "out": 2.5, "media_rel": s, "scene_id": "",
                   "shot_id": "", "label": "Satz"}]
    assert [c["id"] for c in a2] == ["2" * 32, "3" * 32]


def test_audio_tracks_are_free_with_gaps_and_may_overlap_other_tracks(client, auth_headers, ws) -> None:
    img = _media(ws, "images", "a.png", PNG)
    m = _audio(ws, "lied.mp3")
    r = _put_tracks(client, auth_headers, [_clip(media_rel=img, out=10)],
                    [_aclip(id="1" * 32, start=2, out=3, media_rel=m)],
                    [_aclip(id="2" * 32, start=0, out=10, media_rel=m), _aclip(id="3" * 32, start=15, out=1, media_rel=m)])
    assert r.status_code == 200, r.text
    assert r.json()["tracks"][2]["clips"][1]["start"] == 15                 # Lücke bleibt, nichts wird zusammengeschoben


def test_rules_for_audio_tracks(client, auth_headers, ws) -> None:
    img = _media(ws, "images", "a.png", PNG)
    m = _audio(ws, "lied.mp3")
    bad = {
        "Überlappung in einer Spur": ([], [], [_aclip(id="1" * 32, out=5, media_rel=m), _aclip(id="2" * 32, start=4, media_rel=m)]),
        "Bild auf einer Tonspur": ([], [_clip(media_rel=img)], []),
        "Platzhalter auf einer Tonspur": ([], [], [_clip(kind="placeholder")]),
        "Ton auf der Bildspur": ([_aclip(media_rel=m)], [], []),
        "Bild als Ton": ([], [_aclip(media_rel=img)], []),
        "Ton ohne Datei": ([], [_aclip()], []),
        "Datei fehlt": ([], [_aclip(media_rel="atelier/audio/weg.mp3")], []),
        "Pfad mit ..": ([], [_aclip(media_rel="../x.mp3")], []),
        "in = out": ([], [_aclip(media_rel=m, **{"in": 2, "out": 2})], []),
    }
    for name, (v, a1, a2) in bad.items():
        assert _code(_put_tracks(client, auth_headers, v, a1, a2)) == "400 studio_timeline_invalid", name
    tracks = lambda *ids: [{"id": i, "kind": "audio" if i[0] == "A" else "video", "clips": []} for i in ids]   # noqa: E731
    for name, tr in {"unbekannte Spur": tracks("V1", "A3"), "Spur doppelt": tracks("V1", "A1", "A1"),
                     "ohne V1": tracks("A1"), "zu viele": tracks("V1", "A1", "A2", "A2")}.items():
        assert _code(client.put(T, headers=auth_headers, json={"revision": 0, "tracks": tr})) == "400 studio_timeline_invalid", name
    many = lambda off: [_aclip(id=f"{off + i:032x}", start=off + i, out=1, media_rel=m) for i in range(1001)]   # noqa: E731
    assert _code(_put_tracks(client, auth_headers, [], many(0), many(5000))) == "400 studio_timeline_invalid"   # 2.002 > 2.000
    assert not (ws / "studio/timelines/main.json").exists()


def test_deleted_audio_stays_as_missing_and_saves_again(client, auth_headers, ws) -> None:
    m = _audio(ws, "lied.mp3")
    _put_tracks(client, auth_headers, [], [], [_aclip(id="1" * 32, start=3, out=4, media_rel=m, label="Lied")])
    (ws / m).unlink()
    tl = client.get(T, headers=auth_headers).json()
    c = tl["tracks"][2]["clips"][0]
    assert c["kind"] == "audio" and c["missing"] is True and c["media_rel"] == "" and c["start"] == 3 and c["label"] == "Lied"
    r = client.put(T, headers=auth_headers, json=tl)                     # so wie geladen wieder speicherbar
    assert r.status_code == 200, r.text
    assert r.json()["tracks"][2]["clips"][0]["missing"] is True


def test_broken_audio_clip_in_file_is_skipped(client, auth_headers, ws) -> None:
    m = _audio(ws, "lied.mp3")
    (ws / "studio/timelines").mkdir(parents=True)
    (ws / "studio/timelines/main.json").write_text(json.dumps({"revision": 1, "fps": 25, "tracks": [
        {"id": "V1", "clips": []}, {"id": "A2", "clips": [_aclip(id="1" * 32, media_rel=m), {"kind": "audio", "start": "x"},
                                                        _aclip(id="2" * 32, start=2, media_rel=m)]}]}))
    tl = client.get(T, headers=auth_headers).json()
    assert [c["id"] for c in tl["tracks"][2]["clips"]] == ["1" * 32] and tl["tracks"][1]["clips"] == []   # kaputt + Überlappung weg


def test_from_plan_replaces_only_the_picture(client, auth_headers, ws) -> None:
    from _timeline_helpers import _shots
    m = _audio(ws, "lied.mp3")
    _shots(client, auth_headers, ws, [[{"duration": 3}]])
    _put_tracks(client, auth_headers, [], [], [_aclip(id="1" * 32, out=6, media_rel=m)])
    r = client.post(f"{T}/from-plan", headers=auth_headers, json={})       # V1 leer → keine Rückfrage, obwohl Ton da ist
    assert r.status_code == 200, r.text
    tl = r.json()
    assert len(tl["tracks"][0]["clips"]) == 1 and [c["id"] for c in tl["tracks"][2]["clips"]] == ["1" * 32]
    r2 = client.post(f"{T}/from-plan", headers=auth_headers, json={"replace": True})
    assert [c["id"] for c in r2.json()["tracks"][2]["clips"]] == ["1" * 32]    # Ton bleibt beim Ersetzen


def test_overview_counts_clips_of_all_tracks(client, auth_headers, ws) -> None:
    from conftest import MOD_PREFIX, PROJECT_ID
    m = _audio(ws, "lied.mp3")
    _put_tracks(client, auth_headers, [], [], [_aclip(media_rel=m)])
    assert client.get(f"{MOD_PREFIX}/projects/{PROJECT_ID}/overview", headers=auth_headers).json()["clips"] == 1
