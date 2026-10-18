"""Studio B3: freies Bild einem Shot zuweisen und auf die Zeitleiste legen (studio/SPEC.md „Bauplan B3“)."""
from __future__ import annotations

from _gen_helpers import PNG, P
from conftest import MOD_PREFIX, OTHER_PROJECT_ID, PROJECT_ID

T = f"{MOD_PREFIX}/projects/{PROJECT_ID}/timeline"


def _free(ws, name: str = "a.png") -> str:
    d = ws / "studio/media/free"
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_bytes(PNG)
    return f"studio/media/free/{name}"


def _scene_shot(client, h) -> tuple[dict, dict]:
    sc = client.post(f"{P}/scenes", headers=h, json={"title": "Hafen"}).json()
    shot = client.post(f"{P}/scenes/{sc['id']}/shots", headers=h, json={"prompt": "boat", "duration": 4}).json()
    return sc, shot


def test_assign_free_image_to_shot(client, auth_headers, ws) -> None:
    sc, shot = _scene_shot(client, auth_headers)
    rel = _free(ws)
    r = client.put(f"{P}/scenes/{sc['id']}/shots/{shot['id']}/assign", headers=auth_headers, json={"image_rel": rel})
    assert r.status_code == 200, r.text
    s = r.json()
    assert s["image_rel"] == rel and s["variants"] == [rel] and s["status"] == "image_ready"
    saved = client.get(P, headers=auth_headers).json()["scenes"][0]["shots"][0]
    assert saved["image_rel"] == rel and saved["variants"] == [rel]                   # übersteht das Neuladen
    rel2 = _free(ws, "b.png")
    s2 = client.put(f"{P}/scenes/{sc['id']}/shots/{shot['id']}/assign", headers=auth_headers, json={"image_rel": rel2}).json()
    assert s2["variants"] == [rel, rel2] and s2["image_rel"] == rel2
    s3 = client.put(f"{P}/scenes/{sc['id']}/shots/{shot['id']}/variant", headers=auth_headers, json={"image_rel": rel}).json()
    assert s3["image_rel"] == rel                                                      # zurück zur anderen Variante


def test_assign_keeps_video_status(client, auth_headers, ws) -> None:
    sc, shot = _scene_shot(client, auth_headers)
    import json
    f = ws / "studio/scenes" / f"{sc['id']}.json"
    data = json.loads(f.read_text())
    data["shots"][0]["status"] = "done"
    f.write_text(json.dumps(data))
    s = client.put(f"{P}/scenes/{sc['id']}/shots/{shot['id']}/assign", headers=auth_headers, json={"image_rel": _free(ws)}).json()
    assert s["status"] == "done"


def test_assign_rejects_foreign_paths(client, auth_headers, ws) -> None:
    sc, shot = _scene_shot(client, auth_headers)
    (ws / "bilder").mkdir()
    (ws / "bilder/x.png").write_bytes(PNG)
    for rel in ("bilder/x.png", "studio/media/free/fehlt.png", "studio/media/free/../../bilder/x.png", "/etc/passwd", 7):
        r = client.put(f"{P}/scenes/{sc['id']}/shots/{shot['id']}/assign", headers=auth_headers, json={"image_rel": rel})
        assert r.status_code == 400 and r.json()["detail"]["code"] == "studio_assign_invalid", rel
    r = client.put(f"{P}/scenes/{sc['id']}/shots/{'0' * 32}/assign", headers=auth_headers, json={"image_rel": _free(ws)})
    assert r.status_code == 404


def test_append_to_timeline(client, auth_headers, ws) -> None:
    rel = _free(ws)
    r = client.post(f"{T}/append", headers=auth_headers, json={"media_rel": rel})
    assert r.status_code == 200, r.text
    clips = r.json()["tracks"][0]["clips"]
    assert len(clips) == 1 and clips[0]["kind"] == "image" and clips[0]["media_rel"] == rel
    assert clips[0]["start"] == 0 and clips[0]["out"] == 5 and r.json()["revision"] == 1
    r2 = client.post(f"{T}/append", headers=auth_headers, json={"media_rel": _free(ws, "b.png")}).json()
    c2 = r2["tracks"][0]["clips"]
    assert [c["start"] for c in c2] == [0, 5] and r2["revision"] == 2                # hinten angehängt, lückenlos
    assert client.get(T, headers=auth_headers).json()["revision"] == 2


def test_append_rejects_foreign_media(client, auth_headers, ws) -> None:
    (ws / "bilder").mkdir()
    (ws / "bilder/x.png").write_bytes(PNG)
    for rel in ("bilder/x.png", "studio/media/free/fehlt.png", "", None):
        r = client.post(f"{T}/append", headers=auth_headers, json={"media_rel": rel})
        assert r.status_code == 400 and r.json()["detail"]["code"] == "studio_timeline_invalid", rel


def test_foreign_project(client, auth_headers, ws) -> None:
    rel = _free(ws)
    r = client.post(f"{MOD_PREFIX}/projects/{OTHER_PROJECT_ID}/timeline/append", headers=auth_headers, json={"media_rel": rel})
    assert r.status_code == 404
