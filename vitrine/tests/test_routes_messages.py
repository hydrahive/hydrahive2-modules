"""Routen für Einblendungen (E3): senden, auflisten, bestätigen – nur Admin."""
# ruff: noqa: F811 - pytest-Fixtures aus _routes_fixtures werden als gleichnamige Parameter genutzt
from __future__ import annotations


import pytest

pytest.importorskip("hydrahive")
from _routes_fixtures import B, _ffprobe, _h, admin, client, data, env  # noqa: E402, F401 - pytest-Fixtures


def test_nachrichten_senden_liste_bestaetigen(client, admin, data):
    assert client.post(f"{B}/messages", json={"text": "x"}, headers=_h(client, "nutzer")).status_code == 403
    r = client.post(f"{B}/messages", json={"text": "Testnachricht", "kind": "success", "seconds": 30}, headers=admin)
    assert r.status_code == 201, r.text
    mid = r.json()["id"]
    lst = client.get(f"{B}/messages", headers=admin).json()
    assert [(m["id"], m["text"], m["kind"], m["source"]) for m in lst] == [(mid, "Testnachricht", "success", "cockpit")]
    assert client.delete(f"{B}/messages/{mid}", headers=admin).status_code == 204
    assert client.get(f"{B}/messages", headers=admin).json() == []
    assert client.delete(f"{B}/messages/{mid}", headers=admin).status_code == 404


@pytest.mark.parametrize("body", [{"text": ""}, {"text": "x", "kind": "laser"}, {"text": "x", "seconds": 1}, {"text": "x" * 281}])
def test_nachricht_ungueltig_422(client, admin, data, body):
    assert client.post(f"{B}/messages", json=body, headers=admin).status_code == 422


@pytest.mark.parametrize("mid", ["../etwas", "ZZZ", "abc"])
def test_bestaetigen_nur_gueltige_ids(client, admin, data, mid):
    assert client.delete(f"{B}/messages/{mid}", headers=admin).status_code in (404, 422)
