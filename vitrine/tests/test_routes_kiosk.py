"""Kiosk-Routen über den echten Kern-Weg (Geräte-Router mit Rate-Limit + kiosk_auth). Braucht den Kern; ohne → übersprungen."""
# ruff: noqa: F811 - pytest-Fixtures aus _routes_fixtures werden als gleichnamige Parameter genutzt
from __future__ import annotations

import pytest

pytest.importorskip("hydrahive")
from _hh_isolation import only_own_files  # noqa: E402
from _routes_fixtures import _ffprobe, admin, client, data, env  # noqa: E402, F401 - pytest-Fixtures

D = "/api/module-device/vitrine"
KEY = "f" * 64


@pytest.fixture
def key(data):
    with only_own_files(data, "kiosk.key"):
        (data / "kiosk.key").write_text(KEY + "\n")
        yield KEY


def test_seite_mit_schluessel_von_localhost(client, key, monkeypatch):
    from backend import kiosk
    monkeypatch.setattr(kiosk, "LOCAL", frozenset({"testclient"}))   # TestClient meldet sich als „testclient“
    r = client.get(f"{D}/kiosk", params={"k": key})
    assert r.status_code == 200 and "Statuszentrale" in r.text
    assert r.headers["cache-control"] == "no-store"


def test_ohne_oder_falscher_schluessel_404(client, key, monkeypatch):
    from backend import kiosk
    monkeypatch.setattr(kiosk, "LOCAL", frozenset({"testclient"}))
    assert client.get(f"{D}/kiosk").status_code in (404, 422)
    assert client.get(f"{D}/kiosk", params={"k": "x" * 64}).status_code == 404
    assert client.post(f"{D}/back", params={"k": "x" * 64}).status_code == 404


def test_richtiger_schluessel_aber_nicht_localhost_404(client, key):
    assert client.get(f"{D}/kiosk", params={"k": key}).status_code == 404     # „testclient“ ist nicht 127.0.0.1


def test_zurueck_schreibt_wunsch(client, key, data, monkeypatch):
    from backend import kiosk
    from renderer import mode
    monkeypatch.setattr(kiosk, "LOCAL", frozenset({"testclient"}))
    with only_own_files(data, "mode.json"):
        assert client.post(f"{D}/back", params={"k": key}).status_code == 204
        assert mode.take_back_request(data) is True


def test_login_routen_unveraendert_geschuetzt(client, admin):
    assert client.get("/api/modules/vitrine/status").status_code == 401
    st = client.get("/api/modules/vitrine/status", headers=admin).json()
    assert "mode" in st and "dashboard" in st


def test_rueckkehrzeit_speichern_und_grenzen(client, admin, data):
    c = client.get("/api/modules/vitrine/config", headers=admin).json()
    assert c["dashboard_return_seconds"] == 120
    for bad in (29, 1801, "x"):
        assert client.put("/api/modules/vitrine/config", json={**c, "dashboard_return_seconds": bad}, headers=admin).status_code == 422
    assert client.put("/api/modules/vitrine/config", json={**c, "dashboard_return_seconds": 300}, headers=admin).status_code == 200
    assert client.get("/api/modules/vitrine/config", headers=admin).json()["dashboard_return_seconds"] == 300
