"""Gemeinsame Hilfen der Schnitt-Tests (4a, 4b): Medien anlegen, Clips, Fassung speichern, Fehlercode."""
from __future__ import annotations

import json

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
