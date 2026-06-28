"""Agent-Tool-Tests (client gemockt, kein Netz)."""
from __future__ import annotations

from pathlib import Path

from hydrahive.tools.base import ToolContext

from backend import client, tools_read, tools_write


def _ctx() -> ToolContext:
    return ToolContext(session_id="s", agent_id="a", user_id="u", workspace=Path("."))


_STATES = [
    {"entity_id": "light.wohnzimmer", "state": "on", "name": "Wohnzimmer", "domain": "light",
     "unit": None, "attributes": {"friendly_name": "Wohnzimmer", "brightness": 200}},
    {"entity_id": "sensor.bad_temp", "state": "21.5", "name": "Bad Temperatur", "domain": "sensor",
     "unit": "°C", "attributes": {"friendly_name": "Bad Temperatur", "device_class": "temperature"}},
    {"entity_id": "switch.kaffee", "state": "off", "name": "Kaffee", "domain": "switch",
     "unit": None, "attributes": {"friendly_name": "Kaffee"}},
]


# ---- ha_list_entities ----
async def test_list_all(monkeypatch):
    async def fake_states():
        return _STATES
    monkeypatch.setattr(client, "states", fake_states)
    res = await tools_read.LIST_TOOL.execute({}, _ctx())
    assert res.success
    assert res.output["count"] == 3


async def test_list_filter_domain(monkeypatch):
    async def fake_states():
        return _STATES
    monkeypatch.setattr(client, "states", fake_states)
    res = await tools_read.LIST_TOOL.execute({"domain": "light"}, _ctx())
    assert res.success
    assert res.output["count"] == 1
    assert "light.wohnzimmer" in res.output["data"]


async def test_list_filter_search(monkeypatch):
    async def fake_states():
        return _STATES
    monkeypatch.setattr(client, "states", fake_states)
    res = await tools_read.LIST_TOOL.execute({"search": "bad"}, _ctx())
    assert res.success
    assert res.output["count"] == 1


async def test_list_bad_domain():
    res = await tools_read.LIST_TOOL.execute({"domain": "Light!"}, _ctx())
    assert not res.success


async def test_list_config_error(monkeypatch):
    async def boom():
        raise client.HAConfigError("URL fehlt")
    monkeypatch.setattr(client, "states", boom)
    res = await tools_read.LIST_TOOL.execute({}, _ctx())
    assert not res.success
    assert "URL fehlt" in res.error


# ---- ha_get_state ----
async def test_get_state(monkeypatch):
    async def fake_state(eid):
        assert eid == "sensor.bad_temp"
        return _STATES[1]
    monkeypatch.setattr(client, "state", fake_state)
    res = await tools_read.STATE_TOOL.execute({"entity_id": "sensor.bad_temp"}, _ctx())
    assert res.success
    assert "21.5" in res.output["summary"]
    assert "°C" in res.output["summary"]


async def test_get_state_invalid_id():
    res = await tools_read.STATE_TOOL.execute({"entity_id": "kaputt"}, _ctx())
    assert not res.success


# ---- ha_render_template ----
async def test_render(monkeypatch):
    async def fake_render(tpl):
        return "21.5"
    monkeypatch.setattr(client, "render_template", fake_render)
    res = await tools_read.TEMPLATE_TOOL.execute(
        {"template": "{{ states('sensor.bad_temp') }}"}, _ctx())
    assert res.success
    assert res.output["result"] == "21.5"


async def test_render_empty():
    res = await tools_read.TEMPLATE_TOOL.execute({"template": "  "}, _ctx())
    assert not res.success


# ---- ha_call_service ----
async def test_call_service(monkeypatch):
    captured = {}

    async def fake_call(domain, service, data):
        captured.update(domain=domain, service=service, data=data)
        return [{"entity_id": "light.wohnzimmer", "state": "on", "name": "Wohnzimmer",
                 "domain": "light", "unit": None, "attributes": {}}]

    monkeypatch.setattr(client, "call_service", fake_call)
    res = await tools_write.TOOL.execute(
        {"domain": "light", "service": "turn_on", "entity_id": "light.wohnzimmer"}, _ctx())
    assert res.success
    assert captured["data"]["entity_id"] == "light.wohnzimmer"
    assert res.output["changed"] == 1


async def test_call_service_domain_mismatch():
    res = await tools_write.TOOL.execute(
        {"domain": "switch", "service": "turn_on", "entity_id": "light.wohnzimmer"}, _ctx())
    assert not res.success
    assert "passt nicht" in res.error


async def test_call_service_bad_domain():
    res = await tools_write.TOOL.execute(
        {"domain": "Light!", "service": "turn_on"}, _ctx())
    assert not res.success


async def test_call_service_with_data(monkeypatch):
    captured = {}

    async def fake_call(domain, service, data):
        captured.update(data=data)
        return []

    monkeypatch.setattr(client, "call_service", fake_call)
    res = await tools_write.TOOL.execute(
        {"domain": "climate", "service": "set_temperature",
         "entity_id": "climate.bad", "data": {"temperature": 21}}, _ctx())
    assert res.success
    assert captured["data"]["temperature"] == 21
    assert captured["data"]["entity_id"] == "climate.bad"
