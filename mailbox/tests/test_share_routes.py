"""M3a Schritt 2: Routen der Freigaben – nur Besitzer, fremdes Konto 404, Ziel geprüft, Protokoll sichtbar."""
# ruff: noqa: F811 - pytest-Fixtures aus _routes_base werden als gleichnamige Parameter genutzt
from __future__ import annotations

from urllib.parse import quote

import pytest
from _routes_base import B, _h, acc, alice, client, fake_net, rights  # noqa: F401


@pytest.fixture
def project():
    from hydrahive.projects import config as pc
    p = pc.create("Mail-Projekt", llm_model="m", created_by="alice")
    yield p
    pc.delete(p["id"])


def test_freigeben_auflisten_entfernen(client, alice, acc, project):
    t = f"project:{project['id']}"
    r = client.put(f"{B}/accounts/{acc['id']}/shares", json={"target": t}, headers=alice)
    assert r.status_code == 200, r.text
    j = client.get(f"{B}/accounts/{acc['id']}/shares", headers=alice).json()
    assert [(s["target"], s["level"], s["name"]) for s in j["shares"]] == [(t, "read", "Mail-Projekt")]
    assert any(p["id"] == project["id"] for p in j["projects"]) and j["audit"] == []
    assert client.delete(f"{B}/accounts/{acc['id']}/shares/{quote(t)}", headers=alice).status_code == 204
    assert client.delete(f"{B}/accounts/{acc['id']}/shares/{quote(t)}", headers=alice).status_code == 404


def test_fremdes_konto_404(client, acc, project):
    bob = _h(client, "bob")
    t = f"project:{project['id']}"
    assert client.get(f"{B}/accounts/{acc['id']}/shares", headers=bob).status_code == 404
    assert client.put(f"{B}/accounts/{acc['id']}/shares", json={"target": t}, headers=bob).status_code == 404
    assert client.delete(f"{B}/accounts/{acc['id']}/shares/buddy", headers=bob).status_code == 404


@pytest.mark.parametrize("body", [{"target": "project:gibtsnicht0000"}, {"target": "quatsch"},
                                  {"target": "buddy", "level": "send"}, {"target": "buddy", "extra": 1}])
def test_ungueltig_422(client, alice, acc, body):
    assert client.put(f"{B}/accounts/{acc['id']}/shares", json=body, headers=alice).status_code == 422


def test_ohne_modulrecht_403(client, acc):
    carol = _h(client, "carol")
    assert client.get(f"{B}/accounts/{acc['id']}/shares", headers=carol).status_code == 403
