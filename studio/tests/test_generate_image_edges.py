"""Studio 3a: Aufträge nach Neustart, Referenzen, Größe, Varianten-Pfade, alte Daten (studio/SPEC.md „Bauplan Etappe 3“)."""
from __future__ import annotations

import base64
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


def test_provider_without_key_and_with_bad_answers(monkeypatch) -> None:
    """Der echte Anbieter-Aufruf: ohne Schlüssel kein Netzaufruf; Fehlerantworten werden zu Codes."""
    import httpx
    from backend import image_provider as ip
    calls: list = []
    monkeypatch.setattr("hydrahive.llm._config.openrouter_key", lambda: "")
    monkeypatch.setattr(httpx, "post", lambda *a, **k: calls.append(k) or None)
    try:
        ip.request_image(model="m", prompt="p", references=[], aspect_ratio="1:1")
        raise AssertionError("kein Fehler ohne Schlüssel")
    except ip.ProviderError as e:
        assert str(e) == "no_key" and calls == []

    monkeypatch.setattr("hydrahive.llm._config.openrouter_key", lambda: "k")

    def answer(status: int, body):
        return lambda *a, **k: (calls.append(k), httpx.Response(status, json=body))[1]
    for status, body, code in ((400, {"error": {"message": "x"}}, "provider_rejected"), (200, {"data": []}, "empty_answer"),
                               (200, {"data": [{"b64_json": "!!kein base64!!"}]}, "empty_answer")):
        monkeypatch.setattr(httpx, "post", answer(status, body))
        try:
            ip.request_image(model="m", prompt="p", references=["data:x"], aspect_ratio="1:1", seed=7)
            raise AssertionError("kein Fehler")
        except ip.ProviderError as e:
            assert str(e) == code, (status, body)
    sent = calls[-1]["json"]
    assert sent["seed"] == 7 and sent["input_references"] == [{"type": "image_url", "image_url": {"url": "data:x"}}]
    assert calls[-1]["headers"]["Authorization"] == "Bearer k"
    monkeypatch.setattr(httpx, "post", answer(200, {"data": [{"b64_json": base64.b64encode(PNG).decode()}]}))
    assert ip.request_image(model="m", prompt="p", references=[], aspect_ratio="1:1") == PNG
    assert "input_references" not in calls[-1]["json"] and "seed" not in calls[-1]["json"]


def test_old_finished_jobs_are_pruned_running_ones_kept(ws) -> None:
    from backend import jobs
    d = ws / "studio/jobs"
    d.mkdir(parents=True, exist_ok=True)
    for i in range(jobs.KEEP + 5):
        (d / f"{i:032x}.json").write_text(json.dumps({"status": "done", "target": "t", "created_at": f"2026-10-17T10:{i // 60:02d}:{i % 60:02d}Z"}))
    (d / f"{'e' * 32}.json").write_text(json.dumps({"status": "running", "target": "x", "created_at": "2026-01-01T00:00:00Z"}))
    jobs._prune(PROJECT_ID)
    left = {j["id"]: j for j in jobs.list_jobs(PROJECT_ID)}
    assert len([j for j in left.values() if j["status"] == "done"]) == jobs.KEEP
    assert "e" * 32 in left                                             # laufender Auftrag bleibt, auch wenn er alt ist
    assert f"{0:032x}" not in left and f"{jobs.KEEP + 4:032x}" in left  # die ältesten erledigten fliegen raus


def test_attach_keeps_at_most_8_variants_in_order(ws, client, auth_headers) -> None:
    from backend import generate
    from backend import shots as shots_mod
    _, sc, shot = _shot(client, auth_headers, ws, with_ref=False)
    for i in range(10):
        generate._attach(PROJECT_ID, sc["id"], shot["id"], f"studio/media/images/n{i}.png")
    raw = json.loads((ws / f"studio/scenes/{sc['id']}.json").read_text())["shots"][0]["variants"]
    assert raw == [f"studio/media/images/n{i}.png" for i in range(2, 10)]   # schon die gespeicherte Datei ist begrenzt
    assert shots_mod.load_scene(PROJECT_ID, sc["id"])["shots"][0]["image_rel"] == "studio/media/images/n9.png"


def test_prompt_has_no_double_punctuation(client, auth_headers, ws) -> None:
    from backend import generate
    from backend import shots as shots_mod
    _, sc, shot = _shot(client, auth_headers, ws, with_ref=False)
    client.put(f"{P}/scenes/{sc['id']}/shots/{shot['id']}", headers=auth_headers, json={"prompt": "Boot läuft ein.  "})
    scene = shots_mod.load_scene(PROJECT_ID, sc["id"])
    prompt = generate.build_prompt(PROJECT_ID, scene, scene["shots"][0])
    assert ".." not in prompt and ". ." not in prompt and "Boot läuft ein. wide establishing shot" in prompt


def test_jobs_in_the_same_second_keep_their_order(ws) -> None:
    """Aufträge kurz hintereinander: der neueste steht vorn (sonst zeigt die Oberfläche den alten Stand)."""
    from backend import jobs
    ids = []
    for i in range(3):
        ids.append(jobs.start(PROJECT_ID, "image", f"{i}" * 32, "", dict)["id"])
    for t in __import__("threading").enumerate():
        if t.name.startswith("studio-"):
            t.join(5)
    order = [j["id"] for j in jobs.list_jobs(PROJECT_ID) if j["id"] in ids]
    assert order == list(reversed(ids))
