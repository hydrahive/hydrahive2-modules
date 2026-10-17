"""Studio 3a: Aufträge nach Neustart, Referenzen, Größe, Varianten-Pfade, alte Daten (studio/SPEC.md „Bauplan Etappe 3“)."""
from __future__ import annotations

import json

from _gen_helpers import PNG, P, _shot, _wait
from conftest import PROJECT_ID

pytest_plugins = ["_gen_helpers"]                 # Fixture `provider`


def test_running_job_after_restart_is_marked_failed(client, auth_headers, ws) -> None:
    from backend import jobs
    (ws / "studio/jobs").mkdir(parents=True, exist_ok=True)
    (ws / "studio/jobs/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.json").write_text(json.dumps(
        {"id": "a" * 32, "kind": "image", "target": "b" * 32, "scene_id": "c" * 32, "status": "running"}))
    jobs.recover(PROJECT_ID)
    got = {j["id"]: j for j in client.get(f"{P}/jobs", headers=auth_headers).json()["jobs"]}["a" * 32]
    assert got["status"] == "failed" and got["error"] == "interrupted"


def test_references_only_of_shot_elements_and_real_images(client, auth_headers, ws, provider) -> None:
    """Referenzen: nur Bausteine des Shots, nur echte Bilddateien im Projekt (keine Verknüpfungen nach draußen)."""
    import os
    ole, sc, shot = _shot(client, auth_headers, ws)
    (ws / "bilder/mira.png").write_bytes(PNG)
    mira = client.post(f"{P}/elements", headers=auth_headers, json={"kind": "character", "name": "Mira", "references": ["bilder/mira.png"]}).json()
    client.put(f"{P}/scenes/{sc['id']}", headers=auth_headers, json={"element_ids": [ole["id"], mira["id"]]})   # Mira in der Szene, nicht im Shot
    # Referenz nachträglich durch eine Verknüpfung nach draußen ersetzen (Datei wurde nach dem Speichern getauscht)
    outside = ws.parent / "draussen.png"
    outside.write_bytes(PNG)
    (ws / "bilder/ole.png").unlink()
    os.symlink(outside, ws / "bilder/ole.png")
    client.post(f"{P}/scenes/{sc['id']}/shots/{shot['id']}/image", headers=auth_headers, json={})
    assert _wait(client, auth_headers, sc["id"], shot["id"])["status"] == "done"
    assert provider.calls[0]["references"] == []                     # Ole: Symlink → raus; Mira: nicht im Shot → raus
    (ws / "bilder/ole.png").unlink()
    outside.unlink()


def test_too_big_is_not_an_image(monkeypatch) -> None:
    from backend import image_provider
    monkeypatch.setattr(image_provider, "MAX_BYTES", 100)
    assert image_provider.image_kind(PNG) == "png"
    assert image_provider.image_kind(PNG + b"\0" * 200) is None
    assert image_provider.image_kind(b"\xff\xd8\xff\xe0abc") == "jpg"
    assert image_provider.image_kind(b"RIFF\0\0\0\0WEBPVP8 ") == "webp"


def test_variants_only_from_studio_media(client, auth_headers, ws) -> None:
    from backend import shots as shots_mod
    _, sc, _shot_unused = _shot(client, auth_headers, ws, with_ref=False)
    scene = shots_mod.load_scene(PROJECT_ID, sc["id"])
    scene["shots"][0]["variants"] = ["studio/media/images/ok.png", "../../etc/passwd", "atelier/images/x.png",
                                     "studio/media/images/../../x.png", 5]
    saved = shots_mod.save_shots(PROJECT_ID, scene, scene["shots"])[0]
    assert saved["variants"] == ["studio/media/images/ok.png"]


def test_old_shots_without_variants_still_work(client, auth_headers, ws) -> None:
    """Shots aus der Zeit vor 3a (ohne `variants`) kommen beim Lesen vollständig an – sonst stürzt die Oberfläche ab."""
    sc = client.post(f"{P}/scenes", headers=auth_headers, json={"title": "Alt"}).json()
    f = ws / "studio/scenes" / f"{sc['id']}.json"
    data = json.loads(f.read_text())
    data["shots"] = [{"id": "d" * 32, "order": 0, "shot": "wide", "prompt": "alt", "element_ids": [], "duration": 5,
                      "status": "image_ready", "image_rel": "atelier/images/x.png", "video_rel": None}]   # Stand 0.3.0
    f.write_text(json.dumps(data))
    shot = client.get(P, headers=auth_headers).json()["scenes"][0]["shots"][0]
    assert shot["variants"] == [] and shot["image_rel"] == "atelier/images/x.png" and shot["status"] == "image_ready"
