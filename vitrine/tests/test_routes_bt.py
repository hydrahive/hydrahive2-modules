"""S7: Bluetooth-Routen über den echten Kern – Kiosk (Schlüssel + localhost, kein Entfernen) und Cockpit (Recht)."""
# ruff: noqa: F811 - pytest-Fixtures aus _routes_fixtures werden als gleichnamige Parameter genutzt
from __future__ import annotations

import time

import pytest

pytest.importorskip("hydrahive")
from _hh_isolation import only_own_files
from _routes_fixtures import _ffprobe, _h, admin, client, data, env  # noqa: F401 - pytest-Fixtures

from renderer import bt_jobs

D, B = "/api/module-device/vitrine", "/api/modules/vitrine"
KEY = "f" * 64
A3, A4 = "B4:EE:25:ED:70:7F", "B4:EE:25:EE:72:7F"


@pytest.fixture
def key(data):
    with only_own_files(data, "kiosk.key"):
        (data / "kiosk.key").write_text(KEY + "\n")
        yield KEY


@pytest.fixture
def local(monkeypatch):
    from backend import kiosk
    monkeypatch.setattr(kiosk, "LOCAL", frozenset({"testclient"}))


@pytest.fixture
def bt(data):
    with only_own_files(data / "bt"), only_own_files(data / "bt" / "inbox"):
        bt_jobs.write_state(data, {"adapter": {"name": "hydrahive-master", "powered": True},
                                   "window_until": time.time() + 60, "devices": [
            {"address": A3, "name": "RAPOO BT3.0 KB", "rssi": -62, "icon": "input-keyboard", "paired": True},
            {"address": A4, "name": "RAPOO BT4.0 KB", "rssi": -58, "icon": "input-keyboard", "le": True}]})
        yield data
        for p in (data / "bt" / "inbox").glob("*.json"):
            p.unlink()


# --- Kiosk ---------------------------------------------------------------------------------------------------------
def test_kiosk_ansicht(client, key, local, bt):
    r = client.get(f"{D}/bluetooth", params={"k": key})
    assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
    v = r.json()
    assert v["available"] is True and v["devices"][0]["addresses"] == [A3, A4]


@pytest.mark.parametrize("method, path, body", [("get", "/bluetooth", None), ("post", "/bluetooth/scan", None),
                                                ("post", "/bluetooth/pair", {"address": A3})])
def test_kiosk_ohne_schluessel_oder_fremd_404(client, key, bt, method, path, body):
    kw = {"json": body} if body else {}
    assert getattr(client, method)(f"{D}{path}", params={"k": key}, **kw).status_code == 404   # nicht localhost
    assert getattr(client, method)(f"{D}{path}", params={"k": "x" * 64}, **kw).status_code == 404


def test_kiosk_koppeln_legt_auftrag_an(client, key, local, bt):
    assert client.post(f"{D}/bluetooth/pair", params={"k": key}, json={"address": A4}).status_code == 202
    assert [(j["kind"], j["address"]) for j in bt_jobs.take(bt)] == [("pair", A4)]


@pytest.mark.parametrize("body", [{"address": "kaputt"}, {"address": A3, "x": 1}, {}, {"address": 5}])
def test_kiosk_koppeln_kaputt_422(client, key, local, bt, body):
    assert client.post(f"{D}/bluetooth/pair", params={"k": key}, json=body).status_code == 422
    assert bt_jobs.take(bt) == []


def test_kiosk_koppeln_unbekannt_409(client, key, local, bt):
    r = client.post(f"{D}/bluetooth/pair", params={"k": key}, json={"address": "AA:AA:AA:AA:AA:AA"})
    assert r.status_code == 409 and r.json()["detail"]["code"] == "not_seen"


def test_kiosk_kann_nicht_entfernen(client, key, local, bt):
    assert client.delete(f"{D}/bluetooth/{A3}", params={"k": key}).status_code in (404, 405)
    assert bt_jobs.take(bt) == []


def test_kiosk_suche(client, key, local, data):
    with only_own_files(data / "bt"), only_own_files(data / "bt" / "inbox"):
        bt_jobs.write_state(data, {"adapter": {"name": "x", "powered": True}, "window_until": 0, "devices": []})
        assert client.post(f"{D}/bluetooth/scan", params={"k": key}).json() == {"started": True}
        assert [j["kind"] for j in bt_jobs.take(data)] == ["scan"]


def test_kiosk_ohne_dienst_503(client, key, local, data):
    (data / "bt" / "state.json").unlink(missing_ok=True)
    r = client.post(f"{D}/bluetooth/scan", params={"k": key})
    assert r.status_code == 503 and r.json()["detail"]["code"] == "unavailable"


# --- Cockpit -------------------------------------------------------------------------------------------------------
def test_cockpit_braucht_recht(client, bt):
    assert client.get(f"{B}/bluetooth").status_code == 401
    assert client.get(f"{B}/bluetooth", headers=_h(client, "nutzer")).status_code == 403
    assert client.delete(f"{B}/bluetooth/{A3}", headers=_h(client, "nutzer")).status_code == 403
    assert bt_jobs.take(bt) == []


def test_cockpit_ansicht_suche_koppeln_entfernen(client, admin, bt):
    assert client.get(f"{B}/bluetooth", headers=admin).json()["devices"][0]["paired"] is True
    assert client.post(f"{B}/bluetooth/scan", headers=admin).json() == {"started": False}     # Fenster schon offen
    assert client.post(f"{B}/bluetooth/pair", headers=admin, json={"address": A4}).status_code == 202
    assert client.delete(f"{B}/bluetooth/{A3}", headers=admin).status_code == 202
    assert [(j["kind"], j["address"]) for j in bt_jobs.take(bt)] == [("pair", A4), ("remove", A3)]


def test_cockpit_entfernen_regeln(client, admin, bt):
    assert client.delete(f"{B}/bluetooth/{A4}", headers=admin).status_code == 409       # nicht gekoppelt
    assert client.delete(f"{B}/bluetooth/kaputt", headers=admin).status_code == 422
    assert client.delete(f"{B}/bluetooth/..%2F..%2Fetc", headers=admin).status_code in (404, 422)
    assert bt_jobs.take(bt) == []


def test_adresse_wird_schon_an_der_route_geprueft(client, key, local, bt, monkeypatch):
    """Zwei Schichten: das Körper-Schema lehnt ab, bevor die Backend-Logik überhaupt läuft."""
    from backend import bluetooth
    called = []
    monkeypatch.setattr(bluetooth, "pair", lambda *a, **k: called.append(a))
    r = client.post(f"{D}/bluetooth/pair", params={"k": key}, json={"address": "../../etc"})
    assert r.status_code == 422 and called == []
