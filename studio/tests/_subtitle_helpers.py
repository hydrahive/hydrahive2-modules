"""Hilfen der 6a-Tests: Shots mit Sprechtext auf die Zeitleiste legen, Untertitel speichern."""
from __future__ import annotations

from _timeline_helpers import T, _aclip, _audio, _clip
from conftest import MOD_PREFIX, PROJECT_ID

S = f"{MOD_PREFIX}/projects/{PROJECT_ID}/subtitles"
P = f"{MOD_PREFIX}/projects/{PROJECT_ID}/plan"


def cue(i: int, start: float, end: float, text: str = "Hallo") -> dict:
    return {"id": f"{i:032x}", "start": start, "end": end, "text": text}


def put(client, h, cues: list[dict], revision: int = 0, lang: str = "de"):
    return client.put(f"{S}/{lang}", headers=h, json={"revision": revision, "cues": cues})


def film(client, h, ws, shots: list[dict]) -> tuple[dict, list[dict]]:
    """Eine Szene mit Shots (Sprechtext, Dauer) anlegen und ihre Bildclips hintereinander auf V1 legen.
    `voice`: Länge eines an den Shot gebundenen Sprachclips auf A1 (am Bildanfang)."""
    sc = client.post(f"{P}/scenes", headers=h, json={"title": "Hafen"}).json()
    made = [client.post(f"{P}/scenes/{sc['id']}/shots", headers=h,
                        json={"prompt": "x", "duration": s["duration"], "speech": s.get("speech", "")}).json() for s in shots]
    v1, a1, t = [], [], 0.0
    for n, (s, m) in enumerate(zip(shots, made)):
        if s.get("on_timeline", True):
            v1.append(_clip(id=f"{n + 1:032x}", kind="placeholder", start=t, out=s["duration"], scene_id=sc["id"], shot_id=m["id"]))
            if s.get("voice"):
                rel = _audio(ws, f"v{n}.mp3", {"duration": s["voice"]})
                a1.append(_aclip(id=f"{n + 100:032x}", start=t, out=s["voice"], media_rel=rel, scene_id=sc["id"], shot_id=m["id"]))
            t += s["duration"]
    r = client.put(T, headers=h, json={"revision": 0, "fps": 25, "tracks": [
        {"id": "V1", "kind": "video", "clips": v1}, {"id": "A1", "kind": "audio", "clips": a1}, {"id": "A2", "kind": "audio", "clips": []}]})
    assert r.status_code == 200, r.text
    return sc, made
