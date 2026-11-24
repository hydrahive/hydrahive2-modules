"""§7 N3: Knopf „einschalten“ setzt auto:true, „ausschalten“ auto:false, „Übernehmen“ behält den Wert (Kern-Weg, Admin)."""
# ruff: noqa: F811 - pytest-Fixtures aus _routes_fixtures/test_routes_seats_apply werden als gleichnamige Parameter genutzt
from __future__ import annotations

import json

import pytest

pytest.importorskip("hydrahive")
from _routes_fixtures import B, admin, client, data, env  # noqa: F401 - pytest-Fixtures
from test_routes_seats_apply import _save, _wait_idle, sw  # noqa: F401 - pytest-Fixtures


def _auto(data):
    return json.loads((data / "seats.json").read_text()).get("auto")


def test_einschalten_setzt_auto_true(client, admin, data, sw):
    _save(client, admin)
    assert _auto(data) is None                                          # frisch gespeichert: kein Vermerk
    assert client.post(f"{B}/seats/apply", headers=admin).status_code == 200
    _wait_idle()
    assert _auto(data) is True


def test_ausschalten_setzt_auto_false(client, admin, data, sw):
    _save(client, admin)
    (sw.etc / "multiseat-revert.sh").write_text("#!/bin/bash\n")
    assert client.post(f"{B}/seats/revert", headers=admin).status_code == 200
    _wait_idle()
    assert _auto(data) is False


def test_uebernehmen_behaelt_auto(client, admin, data, sw):
    _save(client, admin)
    s = json.loads((data / "seats.json").read_text())
    for value in (False, True):
        (data / "seats.json").write_text(json.dumps({**s, "auto": value}))
        _save(client, admin)
        assert _auto(data) is value
        assert client.get(f"{B}/seats", headers=admin).json()["saved"]["auto"] is value


def test_abgelehntes_einschalten_aendert_auto_nicht(client, admin, data, sw):
    _save(client, admin)
    s = json.loads((data / "seats.json").read_text())
    (data / "seats.json").write_text(json.dumps({**s, "auto": False}))
    (sw.etc / "multiseat.aktiv").write_text("x\n")                      # schon an → 409, Vermerk bleibt
    assert client.post(f"{B}/seats/apply", headers=admin).status_code == 409
    assert _auto(data) is False
