"""Routen für die Display-Vorschau: starten (30 s), beenden – nur Admin, Zeitpunkt geprüft."""
# ruff: noqa: F811 - pytest-Fixtures aus _routes_fixtures werden als gleichnamige Parameter genutzt
from __future__ import annotations

import json

import pytest

pytest.importorskip("hydrahive")
from _routes_fixtures import B, _ffprobe, _h, admin, client, data, env  # noqa: E402, F401 - pytest-Fixtures


def test_vorschau_starten_und_beenden(client, admin, data):
    assert client.post(f"{B}/preview", json={"at": "2026-12-24T19:00"}, headers=_h(client, "nutzer")).status_code == 403
    r = client.post(f"{B}/preview", json={"at": "2026-12-24T19:00"}, headers=admin)
    assert r.status_code == 200, r.text
    assert r.json()["seconds"] == 30
    raw = json.loads((data / "preview.json").read_text())
    assert raw["at"] == "2026-12-24T19:00:00"
    assert client.delete(f"{B}/preview", headers=admin).status_code == 204
    assert not (data / "preview.json").exists()
    assert client.delete(f"{B}/preview", headers=admin).status_code == 204, "beenden ohne laufende Vorschau ist kein Fehler"


@pytest.mark.parametrize("at", ["gestern", "", "2026-13-40T19:00", "1799-01-01T00:00", "2101-01-01T00:00"])
def test_vorschau_ungueltiger_zeitpunkt(client, admin, data, at):
    r = client.post(f"{B}/preview", json={"at": at}, headers=admin)
    assert r.status_code == 422, r.text
    assert not (data / "preview.json").exists()


def test_status_zeigt_vorschau(client, admin, data):
    """Was der Dienst in state.json meldet, kommt im Cockpit an (Hinweistext während der Vorschau)."""
    import time
    (data / "state.json").write_text(json.dumps({"updated": time.time(), "connected": True, "frames": 1,
                                                 "rule": "Weihnachten", "preview": "Vorschau 24.12. 19:00"}))
    st = client.get(f"{B}/status", headers=admin).json()
    assert st["preview"] == "Vorschau 24.12. 19:00" and st["rule"] == "Weihnachten"
