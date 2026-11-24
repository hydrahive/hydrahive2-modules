"""Multiseat M1: GET/PUT /seats über den echten Kern-Weg (nur Admin), mit nachgestellten Systemdaten."""
# ruff: noqa: F811 - pytest-Fixtures aus _routes_fixtures werden als gleichnamige Parameter genutzt
from __future__ import annotations

import json

import pytest

pytest.importorskip("hydrahive")
from _routes_fixtures import B, _h, admin, client, data, env  # noqa: F401 - pytest-Fixtures
from _seats_fixture import NV, build


@pytest.fixture
def sysroot(tmp_path, monkeypatch):
    from backend import seat_routes
    monkeypatch.setattr(seat_routes, "SYS_ROOT", build(tmp_path))
    yield tmp_path


def _assignment(view):
    a = {d["id"]: "seat0" for k in ("gpus", "sound", "inputs") for d in view["devices"][k]}
    a.update({f"gpu:pci:{NV}": "seat1", f"sound:pci:{NV[:-1]}1": "seat1", "input:usb:1-5": "seat1"})
    return a


def test_get_zeigt_geraete_vorschlag_und_hinweis(client, admin, data, sysroot):
    r = client.get(f"{B}/seats", headers=admin)
    assert r.status_code == 200, r.text
    v = r.json()
    assert v["feasible"] is True and v["monitor_detected"] is True and v["applied"] is False
    assert v["assignment"][f"gpu:pci:{NV}"] == "seat1" and v["saved"] is None
    assert {g["vendor"] for g in v["devices"]["gpus"]} == {"AMD", "NVIDIA", "evdi"}


def test_nur_admin(client, data, sysroot):
    assert client.get(f"{B}/seats", headers=_h(client, "nutzer")).status_code == 403
    assert client.put(f"{B}/seats", json={"assignment": {}}, headers=_h(client, "nutzer")).status_code == 403
    assert client.get(f"{B}/seats").status_code == 401


def test_put_speichert_bestaetigte_zuordnung(client, admin, data, sysroot):
    a = _assignment(client.get(f"{B}/seats", headers=admin).json())
    r = client.put(f"{B}/seats", json={"assignment": a}, headers=admin)
    assert r.status_code == 200, r.text
    saved = json.loads((data / "seats.json").read_text())
    assert saved["assignment"] == a and r.json()["applied"] is False
    assert client.get(f"{B}/seats", headers=admin).json()["saved"]["assignment"] == a


@pytest.mark.parametrize("extra", [{"/sys/devices/platform/evdi.0": "seat1"}, {"input:usb:9-9": "seat1"},
                                   {"../../etc/passwd": "seat0"}])
def test_put_lehnt_unbekanntes_geraet_ab(client, admin, data, sysroot, extra):
    a = {**_assignment(client.get(f"{B}/seats", headers=admin).json()), **extra}
    r = client.put(f"{B}/seats", json={"assignment": a}, headers=admin)
    assert r.status_code == 422 and r.json()["detail"]["code"] == "vitrine_seat_unknown_device"
    assert not (data / "seats.json").exists()
