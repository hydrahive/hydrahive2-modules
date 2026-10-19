"""Studio H: Bilder wie im Atelier – berechenbar statt Würfeln (studio/SPEC.md „Bauplan H“). Anbieter ersetzt."""
from __future__ import annotations

import base64
import json
import time
from unittest.mock import AsyncMock, patch

from _draft_helpers import D
from _gen_helpers import PNG, FakeProvider, P

from backend import cast, describe

pytest_plugins = ["_gen_helpers"]
OTHER_PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR42mP4z8AAAAMBAQAY3Y2wAAAAAElFTkSuQmCC")


def _wait(client, h, target: str, timeout: float = 5.0) -> dict:
    end = time.time() + timeout
    while time.time() < end:
        jobs = [j for j in client.get(f"{P}/jobs", headers=h).json()["jobs"] if j["target"] == target]
        if jobs and jobs[0]["status"] in ("done", "failed"):
            return jobs[0]
        time.sleep(0.05)
    raise AssertionError("Auftrag nicht fertig")


def _el(client, h, ws, name: str, kind: str = "character", desc: str = "", photo: bool = False) -> dict:
    refs = []
    if photo:
        (ws / "fotos").mkdir(exist_ok=True)
        (ws / f"fotos/{name}.png").write_bytes(PNG)
        refs = [f"fotos/{name}.png"]
    return client.post(f"{P}/elements", headers=h, json={"kind": kind, "name": name, "description": desc, "references": refs}).json()


def _shot(client, h, text: str, ticked: list[str] | None = None, title: str = "Szene") -> tuple[dict, dict]:
    sc = client.post(f"{P}/scenes", headers=h, json={"title": title, "description": text}).json()
    sh = client.post(f"{P}/scenes/{sc['id']}/shots", headers=h, json={"prompt": text, "element_ids": ticked or []}).json()
    return sc, sh


def _image(client, h, sc: dict, sh: dict, body: dict | None = None) -> None:
    r = client.post(f"{P}/scenes/{sc['id']}/shots/{sh['id']}/image", headers=h, json=body or {})
    assert r.status_code == 202, r.text
    assert _wait(client, h, sh["id"])["status"] == "done"


# --- H1 Aussehen statt Situation -------------------------------------------------------------------------------------

def test_h1_describe_asks_only_for_looks() -> None:
    p = describe.prompt_for({"kind": "character", "name": "Hydra"})
    for word in ("Haltung", "Tätigkeit", "Ort", "Möbel", "Hintergrund"):
        assert word in p, word                                                       # ausdrücklich ausschließen
    assert "NICHT" in p


def test_h1_describe_keeps_situation_words_out(client, auth_headers, ws, monkeypatch) -> None:
    """Liefert die Bild-KI trotzdem eine Situation, landet sie nicht im Aussehen."""
    answer = json.dumps({"description": "Hydra, eine pelzige Kreatur mit fünf bunten Köpfen. Hydra sitzt auf einem Sessel und schaut auf einen Bildschirm.",
                         "style_anchor": "five colorful furry heads, rainbow fur"})
    monkeypatch.setattr("backend.vision_provider.ask", AsyncMock(return_value=answer))
    h = _el(client, auth_headers, ws, "Hydra", photo=True)
    out = client.post(f"{P}/elements/{h['id']}/describe", headers=auth_headers).json()
    assert "Sessel" not in out["description"] and "sitzt" not in out["description"]
    assert "fünf bunten Köpfen" in out["description"]


# --- H2 Nur angehakt -------------------------------------------------------------------------------------------------

def test_h2_named_but_not_ticked_stays_out() -> None:
    els = [{"id": "h", "name": "Hydra", "kind": "character"}, {"id": "a", "name": "Agent", "kind": "object"}]
    scene = {"title": "Hydra erklärt den Agent", "description": "Hydra und ein Agent"}
    assert cast.of_shot(scene, {"prompt": "Hydra zeigt auf den Agent", "element_ids": []}, els) == []
    assert cast.of_shot(scene, {"prompt": "x", "element_ids": ["a", "h"]}, els) == ["h", "a"]      # Figuren zuerst


def test_h2_order_character_place_object() -> None:
    els = [{"id": "o", "name": "Tafel", "kind": "object"}, {"id": "p", "name": "Hörsaal", "kind": "place"},
           {"id": "c", "name": "Hydra", "kind": "character"}]
    assert cast.of_shot({}, {"element_ids": ["o", "p", "c"]}, els) == ["c", "p", "o"]
    assert cast.of_shot({}, {"element_ids": ["o", "x", "c", "c"]}, els) == ["c", "o"]              # Unbekannte/Doppelte raus


def test_h2_prompt_without_untucked_names(client, auth_headers, ws, provider) -> None:
    _el(client, auth_headers, ws, "Buddy", desc="ein anderer Assistent")
    h = _el(client, auth_headers, ws, "Hydra", desc="fünf bunte Köpfe", photo=True)
    sc, sh = _shot(client, auth_headers, "Hydra und Buddy im Hörsaal", ticked=[h["id"]])
    _image(client, auth_headers, sc, sh)
    call = provider.calls[0]
    assert "ein anderer Assistent" not in call["prompt"] and "fünf bunte Köpfe" in call["prompt"]
    assert len(call["references"]) == 1


# --- H3 Figur vorne --------------------------------------------------------------------------------------------------

def test_h3_character_before_place_before_scene(client, auth_headers, ws, provider) -> None:
    client.put(f"{P}/screenplay", headers=auth_headers, json={"look": {"style": "warmer Trickfilm", "palette": []}})
    ort = _el(client, auth_headers, ws, "Hörsaal", kind="place", desc="großer Saal mit Bänken")
    h = _el(client, auth_headers, ws, "Hydra", desc="fünf bunte Köpfe")
    sc, sh = _shot(client, auth_headers, "Hydra steht vorne an der Tafel und erklärt", ticked=[ort["id"], h["id"]])
    _image(client, auth_headers, sc, sh)
    p = provider.calls[0]["prompt"]
    assert p.index("warmer Trickfilm") < p.index("Hydra: fünf bunte Köpfe") < p.index("Hörsaal: großer Saal") < p.index("steht vorne an der Tafel")


# --- H4 Fester Startwert ---------------------------------------------------------------------------------------------

def test_h4_element_gets_fixed_seed(client, auth_headers, ws) -> None:
    h = _el(client, auth_headers, ws, "Hydra")
    assert isinstance(h["seed"], int) and 0 <= h["seed"] < 2**31
    again = client.put(f"{P}/elements/{h['id']}", headers=auth_headers, json={**h, "description": "neu"}).json()
    assert again["seed"] == h["seed"]                                                   # bleibt beim Speichern
    keep = client.put(f"{P}/elements/{h['id']}", headers=auth_headers,
                      json={"kind": "character", "name": "Hydra", "description": "x", "references": []}).json()
    assert keep["seed"] == h["seed"]                                                    # auch ohne seed im Body


def test_h4_image_uses_seed_of_first_character(client, auth_headers, ws, provider) -> None:
    ort = _el(client, auth_headers, ws, "Hörsaal", kind="place")
    h = _el(client, auth_headers, ws, "Hydra")
    assert ort["seed"] != h["seed"]
    sc, sh = _shot(client, auth_headers, "x", ticked=[ort["id"], h["id"]])
    _image(client, auth_headers, sc, sh)
    _image(client, auth_headers, sc, sh)
    assert provider.calls[0]["seed"] == h["seed"] == provider.calls[1]["seed"]


def test_h4_another_image_uses_new_seed(client, auth_headers, ws, provider) -> None:
    h = _el(client, auth_headers, ws, "Hydra")
    sc, sh = _shot(client, auth_headers, "x", ticked=[h["id"]])
    _image(client, auth_headers, sc, sh, {"fresh": True})
    assert provider.calls[0]["seed"] != h["seed"] and isinstance(provider.calls[0]["seed"], int)


def test_h4_no_character_no_seed(client, auth_headers, ws, provider) -> None:
    sc, sh = _shot(client, auth_headers, "leerer Weg im Wald")
    _image(client, auth_headers, sc, sh)
    assert provider.calls[0]["seed"] is None


# --- H5 Geschichten-KI erfindet keine Figuren im Bildtext ------------------------------------------------------------

def test_h5_idea_prompt_forbids_invented_characters(client, auth_headers, ws) -> None:
    from backend import draft_idea
    s = draft_idea.SYSTEM_PROMPT
    assert "only" in s and "characters from the elements list" in s and "never invent" in s
    assert "in the language of the idea" in s and "Prompts in English" not in s


def test_h5_guided_idea_ticks_the_characters(client, auth_headers, ws) -> None:
    """Geführter Weg: Szenen-Figuren werden am einzigen Bild angehakt (nicht nur in der Szene)."""
    answer = json.dumps({"title": "T", "logline": "L",
                         "elements": [{"key": "h", "kind": "character", "name": "Hydra", "description": "fünf Köpfe"}],
                         "scenes": [{"title": "S", "description": "Hydra erklärt", "element_keys": ["h"],
                                     "shots": [{"shot": "", "prompt": "Hydra erklärt", "element_keys": [], "duration": 5}]}]})
    with patch("backend.draft_idea.llm_client.complete", new=AsyncMock(return_value=answer)):
        d = client.post(f"{D}/idea", headers=auth_headers, json={"idea": "x", "length": "30", "shots_per_scene": 1}).json()["draft"]
    assert d["scenes"][0]["shots"][0]["element_keys"] == ["h"]


# --- H6 Bild ändern --------------------------------------------------------------------------------------------------

def test_h6_change_uses_current_image_first(client, auth_headers, ws, monkeypatch) -> None:
    fake = FakeProvider(result=OTHER_PNG)
    monkeypatch.setattr("backend.image_provider.request_image", fake)
    h = _el(client, auth_headers, ws, "Hydra", desc="fünf bunte Köpfe", photo=True)
    sc, sh = _shot(client, auth_headers, "Hydra im Hörsaal", ticked=[h["id"]])
    _image(client, auth_headers, sc, sh)
    first = next(s for s in client.get(P, headers=auth_headers).json()["scenes"] if s["id"] == sc["id"])["shots"][0]["image_rel"]
    r = client.post(f"{P}/scenes/{sc['id']}/shots/{sh['id']}/image", headers=auth_headers, json={"change": "Hydra steht vorne an der Tafel"})
    assert r.status_code == 202
    _wait(client, auth_headers, sh["id"])
    call = fake.calls[1]
    assert call["references"][0].endswith(base64.b64encode(OTHER_PNG).decode())       # gezeigtes Bild zuerst
    assert len(call["references"]) == 2                                                 # + Hydras Foto
    assert "Hydra steht vorne an der Tafel" in call["prompt"] and "Keep everything else" in call["prompt"]
    shot = next(s for s in client.get(P, headers=auth_headers).json()["scenes"] if s["id"] == sc["id"])["shots"][0]
    assert first in shot["variants"] and shot["image_rel"] != first                    # altes bleibt, neues gezeigt


def test_h6_change_needs_image_and_text(client, auth_headers, ws, provider) -> None:
    sc, sh = _shot(client, auth_headers, "x")
    r = client.post(f"{P}/scenes/{sc['id']}/shots/{sh['id']}/image", headers=auth_headers, json={"change": "anders"})
    assert r.status_code == 400 and r.json()["detail"]["code"] == "studio_change_needs_image"
    _image(client, auth_headers, sc, sh)
    for bad in ("", "   ", "x" * 1001, 5):
        r = client.post(f"{P}/scenes/{sc['id']}/shots/{sh['id']}/image", headers=auth_headers, json={"change": bad})
        assert r.status_code == 400 and r.json()["detail"]["code"] == "studio_change_invalid", bad


def test_h4_seed_comes_from_character_not_place(client, auth_headers, ws, provider) -> None:
    """Der Ort steht in der Liste VOR der Figur nicht – trotzdem zählt der Startwert der Figur, nie der des Orts."""
    ort = _el(client, auth_headers, ws, "Hörsaal", kind="place")
    sc, sh = _shot(client, auth_headers, "leerer Saal", ticked=[ort["id"]])
    _image(client, auth_headers, sc, sh)
    assert provider.calls[0]["seed"] is None                                          # nur Ort → kein Startwert


def test_h4_fresh_only_with_real_true(client, auth_headers, ws, provider) -> None:
    h = _el(client, auth_headers, ws, "Hydra")
    sc, sh = _shot(client, auth_headers, "x", ticked=[h["id"]])
    _image(client, auth_headers, sc, sh, {"fresh": "ja"})
    assert provider.calls[0]["seed"] == h["seed"]


def test_h4_seed_cannot_be_set_from_outside(client, auth_headers, ws) -> None:
    for bad in (True, -1, 2**31, "5", 1.5):
        h = client.post(f"{P}/elements", headers=auth_headers, json={"kind": "character", "name": "X", "seed": bad}).json()
        assert type(h["seed"]) is int and 0 <= h["seed"] < 2**31 and h["seed"] is not True, bad


def test_h6_at_most_three_references(client, auth_headers, ws, monkeypatch) -> None:
    fake = FakeProvider(result=OTHER_PNG)
    monkeypatch.setattr("backend.image_provider.request_image", fake)
    a = _el(client, auth_headers, ws, "Hydra", photo=True)
    b = _el(client, auth_headers, ws, "Mira", photo=True)
    c = _el(client, auth_headers, ws, "Ole", photo=True)
    sc, sh = _shot(client, auth_headers, "alle drei", ticked=[a["id"], b["id"], c["id"]])
    _image(client, auth_headers, sc, sh)
    assert len(fake.calls[0]["references"]) == 3
    client.post(f"{P}/scenes/{sc['id']}/shots/{sh['id']}/image", headers=auth_headers, json={"change": "alle lachen"})
    _wait(client, auth_headers, sh["id"])
    assert len(fake.calls[1]["references"]) == 3                                       # gezeigtes Bild + 2 Fotos
