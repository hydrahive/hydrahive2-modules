"""Studio B2: Entwurf übernehmen – neu oder anhängen, Bausteine wiederverwenden, nie Bestehendes ändern."""
from __future__ import annotations

from _draft_helpers import D, P
from conftest import MOD_PREFIX, OTHER_PROJECT_ID


def _draft(**over) -> dict:
    d = {
        "head": {"title": "Licht im Sturm", "logline": "Logline", "description": "", "style": "Noir"},
        "elements": [{"key": "mira", "kind": "character", "name": "Mira", "description": "red coat"},
                     {"key": "turm", "kind": "place", "name": "Leuchtturm", "description": "white"}],
        "scenes": [{"title": "Steg", "description": "Mira wartet", "location": "Hafen", "time_of_day": "Morgen",
                    "element_keys": ["mira", "fremd"],
                    "shots": [{"shot": "wide", "prompt": "harbour", "element_keys": ["mira", "turm"], "duration": 4}]},
                   {"title": "Nacht", "description": "", "element_keys": ["turm"], "shots": []}],
    }
    return {**d, **over}


def test_apply_into_empty_plan(client, auth_headers, ws) -> None:
    r = client.post(f"{D}/apply", headers=auth_headers, json={"draft": _draft()})
    assert r.status_code == 200, r.text
    assert r.json() == {"mode": "new", "scenes": 2, "shots": 1, "elements_new": 2, "elements_reused": 0}
    plan = client.get(P, headers=auth_headers).json()
    assert plan["screenplay"]["title"] == "Licht im Sturm" and plan["screenplay"]["look"]["style"] == "Noir"
    names = {e["id"]: e["name"] for e in plan["elements"]}
    assert sorted(names.values()) == ["Leuchtturm", "Mira"]
    s1, s2 = plan["scenes"]
    assert [s1["title"], s2["title"]] == ["Steg", "Nacht"]
    assert [names[i] for i in s1["element_ids"]] == ["Mira", "Leuchtturm"]                # „fremd“ fällt weg, Turm aus dem Shot
    assert [names[i] for i in s2["element_ids"]] == ["Leuchtturm"]
    shot = s1["shots"][0]
    # Shot-Bausteine müssen in der Szene sein → der Turm wird der Szene mit zugeordnet
    assert sorted(names[i] for i in shot["element_ids"]) == ["Leuchtturm", "Mira"]
    assert shot["status"] == "planned" and shot["image_rel"] is None and shot["prompt"] == "harbour"


def test_append_keeps_existing_and_reuses_elements(client, auth_headers, ws) -> None:
    client.put(f"{P}/screenplay", headers=auth_headers, json={"title": "Mein Film", "look": {"style": ""}})
    mira = client.post(f"{P}/elements", headers=auth_headers, json={"kind": "character", "name": "MIRA", "description": "alt"}).json()
    old = client.post(f"{P}/scenes", headers=auth_headers, json={"title": "Alt", "element_ids": [mira["id"]]}).json()
    client.post(f"{P}/scenes/{old['id']}/shots", headers=auth_headers, json={"prompt": "alter shot"})
    before = client.get(P, headers=auth_headers).json()
    r = client.post(f"{D}/apply", headers=auth_headers, json={"draft": _draft()})
    assert r.json() == {"mode": "append", "scenes": 2, "shots": 1, "elements_new": 1, "elements_reused": 1}
    after = client.get(P, headers=auth_headers).json()
    assert after["screenplay"]["title"] == "Mein Film"                                  # gefüllter Kopf bleibt
    assert after["screenplay"]["look"]["style"] == "Noir"                               # leeres Feld wird gefüllt
    assert after["scenes"][0] == before["scenes"][0]                                   # alte Szene unverändert
    assert [s["title"] for s in after["scenes"]] == ["Alt", "Steg", "Nacht"]
    el = {e["id"]: e for e in after["elements"]}
    assert el[mira["id"]]["description"] == "alt" and len(el) == 2                     # wiederverwendet, nicht geändert
    assert after["scenes"][1]["element_ids"][0] == mira["id"]                            # die vorhandene Mira


def test_apply_checks_everything(client, auth_headers, ws) -> None:
    for draft in ({"scenes": []}, {"scenes": "x"}, _draft(scenes=[{"title": "x"}] * 201),
                  _draft(elements=[{"key": "a", "kind": "auto", "name": "x"}]), "kein dict"):
        r = client.post(f"{D}/apply", headers=auth_headers, json={"draft": draft})
        assert r.status_code == 400 and r.json()["detail"]["code"] == "studio_draft_invalid", str(draft)[:60]
    assert not (ws / "studio" / "scenes").exists()
    long = _draft(scenes=[{"title": "t" * 999, "description": "d", "shots": [{"prompt": "p"}] * 9}])
    r = client.post(f"{D}/apply", headers=auth_headers, json={"draft": long})
    sc = client.get(P, headers=auth_headers).json()["scenes"][0]
    assert r.status_code == 200 and len(sc["title"]) == 200 and len(sc["shots"]) == 5   # Grenzen wie beim Speichern


def test_foreign_project(client, auth_headers) -> None:
    r = client.post(f"{MOD_PREFIX}/projects/{OTHER_PROJECT_ID}/plan/draft/apply", headers=auth_headers, json={"draft": _draft()})
    assert r.status_code == 404
