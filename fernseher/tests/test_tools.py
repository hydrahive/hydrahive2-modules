"""Werkzeuge für Agenten (SPEC.md „Werkzeuge für Agenten“). Nachgebauter Fernseher, kein Netz."""
from __future__ import annotations

from pathlib import Path

import pytest
from backend import tools
from conftest import PSK
from hydrahive.tools.base import ToolContext

NAMES = ["tv_status", "tv_sender_liste", "tv_sender", "tv_lautstaerke", "tv_power", "tv_app"]


def _ctx() -> ToolContext:
    return ToolContext(session_id="s", agent_id="a", user_id="u", workspace=Path("."))


def _tool(name):
    return {t.name: t for t in tools.ALL}[name]


def test_genau_die_sechs_werkzeuge():
    assert [t.name for t in tools.ALL] == NAMES
    for t in tools.ALL:
        assert t.description and t.schema["type"] == "object"
    assert {t.name for t in tools.ALL if t.category == "action"} == {"tv_sender", "tv_lautstaerke", "tv_power",
                                                                      "tv_app"}


async def test_status(configured):
    r = await _tool("tv_status").execute({}, _ctx())
    assert r.success and r.output["channel"] == {"number": 6, "name": "SAT.1"} and r.output["volume"] == 14


async def test_senderliste(configured):
    r = await _tool("tv_sender_liste").execute({}, _ctx())
    assert r.success and r.output["count"] == 6
    assert r.output["channels"][1] == {"number": 2, "name": "ZDF HD"}


async def test_sender_meldet_echten_neuen_zustand(configured):
    r = await _tool("tv_sender").execute({"sender": "ZDF"}, _ctx())
    assert r.success and r.output["channel"] == {"number": 2, "name": "ZDF HD"}
    assert configured.playing["title"] == "ZDF HD"


async def test_sender_ohne_angabe(configured):
    r = await _tool("tv_sender").execute({}, _ctx())
    assert not r.success and "tv_channel_unknown" in r.error


async def test_lautstaerke(configured):
    r = await _tool("tv_lautstaerke").execute({"wert": "-4"}, _ctx())
    assert r.success and r.output["volume"] == 10
    r = await _tool("tv_lautstaerke").execute({"stumm": True}, _ctx())
    assert r.success and r.output["muted"] is True


async def test_lautstaerke_grenze_als_fehler(configured):
    r = await _tool("tv_lautstaerke").execute({"wert": "90"}, _ctx())
    assert not r.success and "tv_volume_limit" in r.error and configured.volume == 14


async def test_lautstaerke_ohne_angabe(configured):
    r = await _tool("tv_lautstaerke").execute({}, _ctx())
    assert not r.success and "tv_volume_invalid" in r.error


async def test_power(configured):
    r = await _tool("tv_power").execute({"an": False}, _ctx())
    assert r.success and r.output["power"] == "standby"


async def test_power_braucht_angabe(configured):
    r = await _tool("tv_power").execute({}, _ctx())
    assert not r.success and configured.power == "active"


async def test_app_ohne_name_liefert_liste(configured):
    r = await _tool("tv_app").execute({}, _ctx())
    assert r.success and r.output["apps"] == ["Netflix", "Plex", "YouTube"]
    assert not any(c[1] == "setActiveApp" for c in configured.calls)


async def test_app_starten(configured):
    r = await _tool("tv_app").execute({"name": "Plex"}, _ctx())
    assert r.success and r.output == {"started": "Plex"}


@pytest.mark.parametrize("name", NAMES)
async def test_kein_schluessel_in_ergebnissen(configured, name):
    configured.psk = "anders"                                 # alle Aufrufe scheitern mit 403
    args = {"tv_sender": {"sender": "ZDF"}, "tv_lautstaerke": {"wert": "10"}, "tv_power": {"an": True},
            "tv_app": {"name": "Plex"}}.get(name, {})
    r = await _tool(name).execute(args, _ctx())
    assert not r.success and "tv_auth_failed" in r.error and PSK not in r.error


async def test_nicht_eingerichtet(fake_tv):
    r = await _tool("tv_status").execute({}, _ctx())
    assert not r.success and "tv_not_configured" in r.error


async def test_sender_aus_app_heraus(configured):
    configured.app_open = True
    r = await _tool("tv_sender").execute({"sender": "ZDF"}, _ctx())
    assert r.success and r.output["channel"] == {"number": 2, "name": "ZDF HD"}


async def test_sender_nicht_gewechselt_ist_fehler(configured):
    configured.ignore_switch = True
    r = await _tool("tv_sender").execute({"sender": "ZDF"}, _ctx())
    assert not r.success and "tv_switch_failed" in r.error
