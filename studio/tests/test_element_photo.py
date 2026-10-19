"""Studio C2: Figur/Ort aus Foto – automatisch im Bild, Beschreibung aus dem Foto (studio/SPEC.md „C2 im Detail“)."""
from __future__ import annotations

import json

import pytest
from _gen_helpers import PNG, P, _wait
from backend import cast

pytest_plugins = ["_gen_helpers"]                 # Fixture `provider`


def _el(eid, name, **kw):
    return {"id": eid, "name": name, "kind": kw.pop("kind", "character"), "references": kw.pop("references", []), **kw}


@pytest.mark.parametrize(("text", "found"), [
    ("Hydra steht am Leuchtturm", ["h", "l"]),
    ("HYDRA lacht", ["h"]),
    ("Hydras Schwester", []),                    # ganzes Wort, nicht Wortteil
    ("die hydraulische Presse", []),
    ("Nah: Hydra, im Regen.", ["h"]),
    ("Kapitän Ole winkt", ["o"]),                # mehrteiliger Name
    ("Ole winkt", []),                           # nur ein Teil des Namens zählt nicht
    ("", []),
])
def test_names_in_text(text, found) -> None:
    els = [_el("h", "Hydra"), _el("l", "Leuchtturm", kind="place"), _el("o", "Kapitän Ole")]
    assert cast.named(text, els) == found


def test_cast_of_shot_merges_ticked_and_named() -> None:
    els = [_el("h", "Hydra"), _el("l", "Leuchtturm"), _el("m", "Mira")]
    scene = {"title": "Sturm am Leuchtturm", "description": "", "element_ids": []}
    shot = {"prompt": "Nahaufnahme", "speech": "Hydra ruft", "element_ids": ["m"]}
    assert cast.of_shot(scene, shot, els) == ["m", "l", "h"]       # angehakt zuerst, dann Szene, dann Shot – ohne Doppelte


def _setup(client, h, ws, *, prompt: str, ref: bool = True):
    client.put(f"{P}/screenplay", headers=h, json={"models": {"image": "test/billig"}})
    refs = []
    if ref:
        (ws / "bilder").mkdir(exist_ok=True)
        (ws / "bilder/hydra.png").write_bytes(PNG)
        refs = ["bilder/hydra.png"]
    hydra = client.post(f"{P}/elements", headers=h, json={"kind": "character", "name": "Hydra", "description": "Drache mit drei Köpfen",
                                                         "style_anchor": "grüne Schuppen", "references": refs}).json()
    sc = client.post(f"{P}/scenes", headers=h, json={"title": "Am Meer"}).json()               # Hydra NICHT in der Szene angehakt
    shot = client.post(f"{P}/scenes/{sc['id']}/shots", headers=h, json={"prompt": prompt}).json()
    return hydra, sc, shot


def test_named_element_goes_into_the_image(client, auth_headers, ws, provider) -> None:
    """Hydra steht nur im Shot-Text – trotzdem bekommt die Bild-KI Beschreibung, Aussehen und Foto."""
    _, sc, shot = _setup(client, auth_headers, ws, prompt="Hydra fliegt über das Meer")
    client.post(f"{P}/scenes/{sc['id']}/shots/{shot['id']}/image", headers=auth_headers, json={})
    assert _wait(client, auth_headers, sc["id"], shot["id"])["status"] == "done"
    call = provider.calls[0]
    assert "Hydra: Drache mit drei Köpfen" in call["prompt"] and "grüne Schuppen" in call["prompt"]
    assert len(call["references"]) == 1


def test_unnamed_element_stays_out(client, auth_headers, ws, provider) -> None:
    _, sc, shot = _setup(client, auth_headers, ws, prompt="Wellen am Strand")
    client.post(f"{P}/scenes/{sc['id']}/shots/{shot['id']}/image", headers=auth_headers, json={})
    _wait(client, auth_headers, sc["id"], shot["id"])
    assert "Hydra" not in provider.calls[0]["prompt"] and provider.calls[0]["references"] == []


def test_ticked_without_scene_still_counts(client, auth_headers, ws, provider) -> None:
    """Angehakt im Shot zählt auch, wenn die Figur nicht in der Szene steht (früher wurde das stillschweigend entfernt)."""
    hydra, sc, shot = _setup(client, auth_headers, ws, prompt="sie fliegt")
    r = client.put(f"{P}/scenes/{sc['id']}/shots/{shot['id']}", headers=auth_headers, json={"element_ids": [hydra["id"]]})
    assert r.json()["element_ids"] == [hydra["id"]]
    client.post(f"{P}/scenes/{sc['id']}/shots/{shot['id']}/image", headers=auth_headers, json={})
    _wait(client, auth_headers, sc["id"], shot["id"])
    assert "Hydra" in provider.calls[0]["prompt"]


def test_plan_shows_cast_per_shot(client, auth_headers, ws) -> None:
    hydra, sc, _ = _setup(client, auth_headers, ws, prompt="Hydra fliegt")
    shot = next(s for s in client.get(P, headers=auth_headers).json()["scenes"] if s["id"] == sc["id"])["shots"][0]
    assert shot["cast"] == [hydra["id"]]


# --- Beschreibung aus dem Foto ---------------------------------------------------------------------------------------

class FakeVision:
    def __init__(self, answer: str | Exception) -> None:
        self.answer, self.calls = answer, []

    async def __call__(self, *, model, image_url, prompt):
        self.calls.append({"model": model, "image_url": image_url, "prompt": prompt})
        if isinstance(self.answer, Exception):
            raise self.answer
        return self.answer


@pytest.fixture
def vision(monkeypatch):
    fake = FakeVision(json.dumps({"description": "Ein grüner Drache mit drei Köpfen.", "style_anchor": "grüne Schuppen, gelbe Augen"}))
    monkeypatch.setattr("backend.vision_provider.ask", fake)
    return fake


def test_describe_from_photo(client, auth_headers, ws, vision) -> None:
    hydra, _, _ = _setup(client, auth_headers, ws, prompt="x")
    client.put(f"{P}/elements/{hydra['id']}", headers=auth_headers, json={**hydra, "description": "", "style_anchor": ""})
    r = client.post(f"{P}/elements/{hydra['id']}/describe", headers=auth_headers, json={})
    assert r.status_code == 200, r.text
    assert r.json()["description"] == "Ein grüner Drache mit drei Köpfen." and r.json()["style_anchor"] == "grüne Schuppen, gelbe Augen"
    call = vision.calls[0]
    assert call["image_url"].startswith("data:image/png;base64,") and call["model"] == "google/gemini-2.5-flash"
    assert "Hydra" in call["prompt"] and "Figur" in call["prompt"]
    saved = next(e for e in client.get(P, headers=auth_headers).json()["elements"] if e["id"] == hydra["id"])
    assert saved["description"] == "Ein grüner Drache mit drei Köpfen."              # gespeichert


def test_describe_answer_in_code_fence_and_too_long(client, auth_headers, ws, vision) -> None:
    vision.answer = "```json\n" + json.dumps({"description": "x" * 5000, "style_anchor": "y"}) + "\n```"
    hydra, _, _ = _setup(client, auth_headers, ws, prompt="x")
    r = client.post(f"{P}/elements/{hydra['id']}/describe", headers=auth_headers, json={})
    assert r.status_code == 200 and len(r.json()["description"]) == 4000


def test_describe_uses_model_from_screenplay(client, auth_headers, ws, vision) -> None:
    hydra, _, _ = _setup(client, auth_headers, ws, prompt="x")
    client.put(f"{P}/screenplay", headers=auth_headers, json={"models": {"vision": "openai/gpt-4o"}})
    client.post(f"{P}/elements/{hydra['id']}/describe", headers=auth_headers, json={})
    assert vision.calls[0]["model"] == "openai/gpt-4o"


@pytest.mark.parametrize(("answer", "code"), [("kein json", "studio_describe_failed"), (json.dumps({"description": ""}), "studio_describe_failed"),
                                              (RuntimeError("no_key"), "studio_describe_no_key")])
def test_describe_errors(client, auth_headers, ws, vision, answer, code) -> None:
    vision.answer = answer
    if isinstance(answer, RuntimeError):
        from backend import vision_provider
        vision.answer = vision_provider.VisionError("no_key")
    hydra, _, _ = _setup(client, auth_headers, ws, prompt="x")
    r = client.post(f"{P}/elements/{hydra['id']}/describe", headers=auth_headers, json={})
    assert r.status_code in (400, 502) and r.json()["detail"]["code"] == code
    saved = next(e for e in client.get(P, headers=auth_headers).json()["elements"] if e["id"] == hydra["id"])
    assert saved["description"] == "Drache mit drei Köpfen"                          # nichts überschrieben


def test_describe_without_photo(client, auth_headers, ws, vision) -> None:
    hydra, _, _ = _setup(client, auth_headers, ws, prompt="x", ref=False)
    r = client.post(f"{P}/elements/{hydra['id']}/describe", headers=auth_headers, json={})
    assert r.status_code == 400 and r.json()["detail"]["code"] == "studio_describe_no_image" and not vision.calls


def test_describe_unknown_element(client, auth_headers, vision) -> None:
    r = client.post(f"{P}/elements/{'0' * 32}/describe", headers=auth_headers, json={})
    assert r.status_code == 404


# --- aus der Bibliothek ----------------------------------------------------------------------------------------------

def test_element_from_library_image(client, auth_headers, ws) -> None:
    (ws / "studio/media/uploads").mkdir(parents=True)
    (ws / "studio/media/uploads/a.png").write_bytes(PNG)
    r = client.post(f"{P}/elements/from-image", headers=auth_headers, json={"rel": "studio/media/uploads/a.png", "kind": "place", "name": "Leuchtturm"})
    assert r.status_code == 200, r.text
    el = r.json()
    assert el["kind"] == "place" and el["name"] == "Leuchtturm" and el["references"] == ["studio/media/uploads/a.png"]


@pytest.mark.parametrize("body", [{"rel": "studio/media/uploads/fehlt.png", "kind": "character", "name": "X"},
                                  {"rel": "../draussen.png", "kind": "character", "name": "X"},
                                  {"rel": "studio/media/uploads/a.png", "kind": "nix", "name": "X"},
                                  {"rel": "studio/media/uploads/a.png", "kind": "character", "name": ""}])
def test_element_from_library_rejects(client, auth_headers, ws, body) -> None:
    (ws / "studio/media/uploads").mkdir(parents=True, exist_ok=True)
    (ws / "studio/media/uploads/a.png").write_bytes(PNG)
    r = client.post(f"{P}/elements/from-image", headers=auth_headers, json=body)
    assert r.status_code == 400
    assert client.get(P, headers=auth_headers).json()["elements"] == []


@pytest.mark.parametrize(("kind", "word"), [("character", "Figur"), ("place", "Ort"), ("object", "Gegenstand")])
def test_prompt_names_the_kind(kind, word) -> None:
    from backend import describe
    p = describe.prompt_for({"kind": kind, "name": "Hydra"})
    assert f"die {word} „Hydra“" in p and "JSON" in p
