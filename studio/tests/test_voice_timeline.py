"""Studio 5c-1: Sprache gehört zum Shot – „Aus dem Drehbuch übernehmen“ legt sie an den Anfang des Bildclips (Spec 5c)."""
from __future__ import annotations

import json

from _timeline_helpers import T
from _voice_helpers import P, scene_with_shot, wait_job

pytest_plugins = ["_voice_helpers"]                # Fixture `voice`

def _speech(client, h, sc, s):
    client.post(f"{P}/scenes/{sc['id']}/shots/{s['id']}/speech", headers=h)
    return wait_job(client, h, s["id"])["result"]["voice_rel"]


def test_from_plan_puts_speech_at_the_start_of_its_picture(client, auth_headers, ws, voice) -> None:
    sc, a = scene_with_shot(client, auth_headers, speech="Eins")
    b = client.post(f"{P}/scenes/{sc['id']}/shots", headers=auth_headers, json={"prompt": "x", "duration": 3, "speech": "Zwei"}).json()
    va, vb = _speech(client, auth_headers, sc, a), _speech(client, auth_headers, sc, b)
    tl = client.post(f"{T}/from-plan", headers=auth_headers, json={}).json()
    v1, a1 = tl["tracks"][0]["clips"], tl["tracks"][1]["clips"]
    assert [c["start"] for c in v1] == [0, 4]
    assert [(c["media_rel"], c["start"], c["shot_id"], round(c["out"] - c["in"], 2)) for c in a1] == [
        (va, 0, a["id"], 1.5), (vb, 4, b["id"], 1.5)]
    assert all(c["label"] for c in a1)


def test_speech_longer_than_its_picture_is_cut(client, auth_headers, ws, voice) -> None:
    from _voice_helpers import wav
    voice.data = wav(6.0)
    sc, a = scene_with_shot(client, auth_headers, speech="lang", duration=2)
    _speech(client, auth_headers, sc, a)
    tl = client.post(f"{T}/from-plan", headers=auth_headers, json={}).json()
    c = tl["tracks"][1]["clips"][0]
    assert (c["start"], c["in"], c["out"]) == (0, 0, 2)


def test_replace_keeps_free_voice_and_music_but_renews_bound_speech(client, auth_headers, ws, voice) -> None:
    from _timeline_helpers import _aclip, _audio
    sc, a = scene_with_shot(client, auth_headers, speech="Eins")
    _speech(client, auth_headers, sc, a)
    tl = client.post(f"{T}/from-plan", headers=auth_headers, json={}).json()
    m = _audio(ws, "lied.mp3")
    free = _aclip(id="9" * 32, start=10, out=2, media_rel=m)
    tracks = tl["tracks"]
    tracks[1]["clips"].append(free)                                       # freier Sprachclip (ohne shot_id)
    tracks[2]["clips"] = [_aclip(id="8" * 32, out=3, media_rel=m)]
    client.put(T, headers=auth_headers, json={"revision": tl["revision"], "fps": 25, "tracks": tracks})
    new = _speech(client, auth_headers, sc, a)
    tl2 = client.post(f"{T}/from-plan", headers=auth_headers, json={"replace": True}).json()
    a1 = tl2["tracks"][1]["clips"]
    assert [c["media_rel"] for c in a1] == [new, m]                       # gebundene Sprache neu, freie bleibt
    assert [c["id"] for c in tl2["tracks"][2]["clips"]] == ["8" * 32]


def test_bound_clip_survives_save_and_load(client, auth_headers, ws, voice) -> None:
    sc, a = scene_with_shot(client, auth_headers, speech="Eins")
    _speech(client, auth_headers, sc, a)
    tl = client.post(f"{T}/from-plan", headers=auth_headers, json={}).json()
    got = client.get(T, headers=auth_headers).json()
    assert got["tracks"][1]["clips"][0]["shot_id"] == a["id"]
    saved = json.loads((ws / "studio/timelines/main.json").read_text())
    assert saved["tracks"][1]["clips"][0]["shot_id"] == a["id"]
    _ = tl


def test_replace_drops_old_bound_speech_of_shots_without_speech(client, auth_headers, ws, voice) -> None:
    """Gebundene Sprache wird beim Ersetzen immer neu aus dem Drehbuch gelegt – hat der Shot keine mehr, fällt sie weg."""
    sc, a = scene_with_shot(client, auth_headers, speech="Eins")
    _speech(client, auth_headers, sc, a)
    tl = client.post(f"{T}/from-plan", headers=auth_headers, json={}).json()
    assert len(tl["tracks"][1]["clips"]) == 1
    f = ws / f"studio/scenes/{sc['id']}.json"
    data = json.loads(f.read_text())
    data["shots"][0]["voice_rel"] = None                                 # Sprache am Shot entfernt
    f.write_text(json.dumps(data))
    tl2 = client.post(f"{T}/from-plan", headers=auth_headers, json={"replace": True}).json()
    assert tl2["tracks"][1]["clips"] == []
