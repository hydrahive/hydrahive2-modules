"""S8: Licht im Cockpit – Einstellung (PUT /config), Lichtfarbe je Regel, Status und Vorschau. Über den echten Kern-Weg."""
# ruff: noqa: F811 - pytest-Fixtures aus _routes_fixtures werden als gleichnamige Parameter genutzt
from __future__ import annotations

import json

import pytest

pytest.importorskip("hydrahive")
from _routes_fixtures import B, _ffprobe, _h, admin, client, data, env  # noqa: E402, F401 - pytest-Fixtures


def test_licht_vorgaben_kommen_mit(client, admin, data):
    c = client.get(f"{B}/config", headers=admin).json()
    assert c["light"]["brightness"] == 80 and c["light"]["states"]["working"]["effect"] == "breathing"


def test_licht_speichern(client, admin, data):
    c = client.get(f"{B}/config", headers=admin).json()
    c["light"]["brightness"] = 55
    c["light"]["states"]["error"]["color"] = "#ff00aa"
    c["light"]["seasons"]["winter"]["effect"] = "breathing"
    r = client.put(f"{B}/config", json=c, headers=admin)
    assert r.status_code == 200, r.text
    saved = json.loads((data / "config.json").read_text())["light"]
    assert saved["brightness"] == 55 and saved["states"]["error"]["color"] == "FF00AA"
    assert saved["seasons"]["winter"]["effect"] == "breathing"


def test_altes_cockpit_ohne_licht(client, admin, data):
    c = client.get(f"{B}/config", headers=admin).json()
    c.pop("light")
    assert client.put(f"{B}/config", json=c, headers=admin).status_code == 200
    assert json.loads((data / "config.json").read_text())["light"]["brightness"] == 80


@pytest.mark.parametrize("patch", [
    {"brightness": 101}, {"brightness": "hell"}, {"enabled": "ja"}, {"fremd": 1}, {"error_blink_seconds": 9999},
])
def test_licht_ungueltig_422(client, admin, data, patch):
    c = client.get(f"{B}/config", headers=admin).json()
    c["light"].update(patch)
    assert client.put(f"{B}/config", json=c, headers=admin).status_code == 422
    assert not (data / "config.json").exists()


def test_licht_zustand_ungueltig_422(client, admin, data):
    c = client.get(f"{B}/config", headers=admin).json()
    c["light"]["states"]["working"]["effect"] = "rainbow"
    assert client.put(f"{B}/config", json=c, headers=admin).status_code == 422


def _rule(**extra) -> dict:
    return {"id": "h", "name": "Halloween", "kind": "range", "from": "10-31", "to": "10-31", "priority": 50,
            "enabled": True, "videos": [], **extra}


def test_regel_mit_lichtfarbe(client, admin, data):
    c = client.get(f"{B}/config", headers=admin).json()
    c["rules"] = [_rule(light_color="#ff6a00", light_effect="breathing"), {**_rule(), "id": "x", "name": "Ohne"}]
    r = client.put(f"{B}/config", json=c, headers=admin)
    assert r.status_code == 200, r.text
    rules = json.loads((data / "config.json").read_text())["rules"]
    assert rules[0]["light_color"] == "FF6A00" and rules[0]["light_effect"] == "breathing"
    assert "light_color" not in rules[1] and "light_effect" not in rules[1]


@pytest.mark.parametrize("extra", [{"light_color": "orange"}, {"light_color": "FF6A00", "light_effect": "wave"}])
def test_regel_mit_falscher_lichtfarbe_422(client, admin, data, extra):
    c = client.get(f"{B}/config", headers=admin).json()
    c["rules"] = [_rule(**extra)]
    assert client.put(f"{B}/config", json=c, headers=admin).status_code == 422


def test_status(client, admin, data):
    assert client.get(f"{B}/light", headers=admin).json() == {"available": False}
    (data / "light.json").write_text(json.dumps({"device": "B850", "state": "working", "color": "0060FF",
                                                 "effect": "breathing", "label": "", "preview": None,
                                                 "error": None, "updated": 1.0}))
    st = client.get(f"{B}/light", headers=admin).json()
    assert st["available"] is True and st["state"] == "working" and st["device"] == "B850"
    assert set(st["preview_states"]) >= {"error", "warning", "done", "working", "winter", "night", "occasion"}


def test_vorschau(client, admin, data):
    r = client.post(f"{B}/light/preview", json={"state": "error"}, headers=admin)
    assert r.status_code == 200 and r.json()["seconds"] == 15
    assert json.loads((data / "light_preview.json").read_text())["state"] == "error"
    assert client.post(f"{B}/light/preview", json={"state": "../x"}, headers=admin).status_code == 422


def test_licht_routen_nur_mit_recht(client, data):
    h = _h(client, "nutzer")
    assert client.get(f"{B}/light", headers=h).status_code == 403
    assert client.post(f"{B}/light/preview", json={"state": "error"}, headers=h).status_code == 403
