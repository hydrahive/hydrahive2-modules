"""Studio G3: Bilder im geführten Weg (studio/SPEC.md „Bauplan G3“). Der Bild-Anbieter wird ersetzt."""
from __future__ import annotations

import time

from _gen_helpers import PNG, FakeProvider, P

pytest_plugins = ["_gen_helpers"]                 # Fixture `provider`


def _setup(client, h) -> tuple[dict, dict, dict, dict]:
    hydra = client.post(f"{P}/elements", headers=h, json={"kind": "character", "name": "Hydra", "description": "five heads"}).json()
    mira = client.post(f"{P}/elements", headers=h, json={"kind": "character", "name": "Mira", "description": "red coat"}).json()
    sc = client.post(f"{P}/scenes", headers=h, json={"title": "Wald", "description": "Hydra und Mira im Wald"}).json()
    shot = client.post(f"{P}/scenes/{sc['id']}/shots", headers=h, json={"prompt": "Hydra und Mira im Wald"}).json()
    return hydra, mira, sc, shot


def _cast(client, h, sc_id: str) -> list[str]:
    sc = next(s for s in client.get(P, headers=h).json()["scenes"] if s["id"] == sc_id)
    return sc["shots"][0]["cast"]


def test_cast_is_what_is_ticked(client, auth_headers, ws) -> None:
    """H2: genannt reicht nicht mehr; angehakt = im Bild."""
    hydra, mira, sc, shot = _setup(client, auth_headers)
    assert _cast(client, auth_headers, sc["id"]) == []
    client.put(f"{P}/scenes/{sc['id']}/shots/{shot['id']}", headers=auth_headers, json={"element_ids": [mira["id"], hydra["id"]]})
    assert sorted(_cast(client, auth_headers, sc["id"])) == sorted([hydra["id"], mira["id"]])


def test_excluded_beats_ticked(client, auth_headers, ws) -> None:
    _, mira, sc, shot = _setup(client, auth_headers)
    client.put(f"{P}/scenes/{sc['id']}/shots/{shot['id']}", headers=auth_headers,
               json={"element_ids": [mira["id"]], "excluded_ids": [mira["id"]]})
    assert mira["id"] not in _cast(client, auth_headers, sc["id"])


def test_excluded_only_known_ids(client, auth_headers, ws) -> None:
    hydra, _, sc, shot = _setup(client, auth_headers)
    out = client.put(f"{P}/scenes/{sc['id']}/shots/{shot['id']}", headers=auth_headers,
                     json={"excluded_ids": ["f" * 32, hydra["id"], hydra["id"], 3]}).json()
    assert out["excluded_ids"] == [hydra["id"]]
    assert client.put(f"{P}/scenes/{sc['id']}/shots/{shot['id']}", headers=auth_headers, json={"excluded_ids": "x"}).json()["excluded_ids"] == []


def test_deleted_element_leaves_excluded(client, auth_headers, ws) -> None:
    _, mira, sc, shot = _setup(client, auth_headers)
    client.put(f"{P}/scenes/{sc['id']}/shots/{shot['id']}", headers=auth_headers, json={"excluded_ids": [mira["id"]]})
    client.delete(f"{P}/elements/{mira['id']}", headers=auth_headers)
    sc2 = next(s for s in client.get(P, headers=auth_headers).json()["scenes"] if s["id"] == sc["id"])
    assert sc2["shots"][0]["excluded_ids"] == []


def test_excluded_leaves_prompt_and_references(client, auth_headers, ws, provider) -> None:
    (ws / "f.png").write_bytes(PNG)
    hydra, mira, sc, shot = _setup(client, auth_headers)
    client.put(f"{P}/elements/{mira['id']}", headers=auth_headers, json={**mira, "references": ["f.png"]})
    client.put(f"{P}/scenes/{sc['id']}/shots/{shot['id']}", headers=auth_headers,
               json={"element_ids": [hydra["id"], mira["id"]], "excluded_ids": [mira["id"]]})
    client.post(f"{P}/scenes/{sc['id']}/shots/{shot['id']}/image", headers=auth_headers)
    end = time.time() + 5
    while not provider.calls and time.time() < end:
        time.sleep(0.05)
    call = provider.calls[0]
    assert "red coat" not in call["prompt"] and "five heads" in call["prompt"]
    assert call["references"] == []                                                      # Miras Foto geht nicht mit


def test_batch_reports_current_shot(client, auth_headers, ws, monkeypatch) -> None:
    monkeypatch.setattr("backend.image_provider.request_image", FakeProvider(delay=0.4))
    _, _, _, shot = _setup(client, auth_headers)
    job = client.post(f"{P}/batch/images_all", headers=auth_headers).json()
    seen = ""
    end = time.time() + 5
    while time.time() < end:
        j = next(x for x in client.get(f"{P}/jobs", headers=auth_headers).json()["jobs"] if x["id"] == job["id"])
        seen = seen or j["progress"].get("current_shot", "")
        if j["status"] == "done":
            break
        time.sleep(0.05)
    assert seen == shot["id"]
    assert j["progress"]["current_shot"] == ""                                            # am Ende leer
