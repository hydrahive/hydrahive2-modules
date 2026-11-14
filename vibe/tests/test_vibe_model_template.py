"""Modell eines Vibe-Projekts über das Agenten-Template `modul-schnell` (Vibe 0.2.0, Kern E5, Option B).

Wählbar sind nur die Modelle der Kette; die Wahl ist das Sitzungsmodell des Vibe-Chats, das Template bleibt dahinter.
"""
from __future__ import annotations

import pytest
from backend import container, jobs, network, provision

B = "/api/modules/vibe"


@pytest.fixture
def env(setup_test_env, db_ready, fake_incus, monkeypatch):
    from hydrahive.projects import execution
    monkeypatch.setattr(network, "_host_networks", lambda: set())
    monkeypatch.setattr(network, "_host_addresses", lambda: set())
    monkeypatch.setattr(execution, "_container_exists", lambda name: container.is_vibe_name(name))

    async def fake_setup(pid, report, *, start_at=""):
        for s in provision.STEPS:
            report(s.key)
    monkeypatch.setattr(provision, "setup", fake_setup)
    jobs.reset()
    return fake_incus


def _chain():
    from hydrahive.agents import templates as tpl
    return tpl.get("modul-schnell")["chain"]


def _create(client, headers, **extra):
    return client.post(B + "/projects", json={"name": "App", **extra}, headers=headers)


def _session_override(pid):
    from backend import chat, state
    from hydrahive.db import sessions as sessions_db
    sid = chat.session_id(state.get_row(pid)["agent_id"])
    return (sessions_db.get(sid).metadata or {}).get("model_override") if sid else None


def test_liste_ist_die_kette(env, client, admin_headers):
    d = client.get(B + "/models", headers=admin_headers).json()
    assert [i["id"] for i in d["items"]] == _chain()
    assert d["default"] == _chain()[0] and d["default_listed"] is True
    assert [i["provider"] for i in d["items"]][:3] == ["Primär", "Failover", "Notfall"][:len(_chain())]


def test_anlegen_bindet_an_template(env, client, admin_headers):
    from backend import state
    from hydrahive.agents import config as agent_config
    pid = _create(client, admin_headers).json()["project_id"]
    agent = agent_config.get(state.get_row(pid)["agent_id"])
    assert agent["template"] == "modul-schnell" and agent["managed_by"] == "vibe"
    assert client.get(B + "/state", headers=admin_headers).json()["projects"][0]["model"] == _chain()[0]


def test_anlegen_mit_modell_aus_der_kette_wird_sitzungsmodell(env, client, admin_headers):
    second = _chain()[1]
    pid = _create(client, admin_headers, model=second).json()["project_id"]
    assert _session_override(pid) == second
    assert client.get(B + "/state", headers=admin_headers).json()["projects"][0]["model"] == second


def test_anlegen_mit_fremdem_modell_abgelehnt(env, client, admin_headers):
    r = _create(client, admin_headers, model="claude-fable-5")
    assert r.status_code == 400 and r.json()["detail"]["code"] == "vibe_model_unavailable"
    assert client.get(B + "/state", headers=admin_headers).json()["projects"] == []


def test_wechseln_innerhalb_der_kette(env, client, admin_headers):
    pid = _create(client, admin_headers).json()["project_id"]
    second = _chain()[1]
    r = client.post(f"{B}/projects/{pid}/model", json={"model": second}, headers=admin_headers)
    assert r.status_code == 200 and r.json() == {"model": second}
    assert _session_override(pid) == second
    assert client.get(B + "/state", headers=admin_headers).json()["projects"][0]["model"] == second
    client.post(f"{B}/projects/{pid}/model", json={"model": _chain()[0]}, headers=admin_headers)
    assert _session_override(pid) is None                        # zurück auf Primär = Template entscheidet


def test_wechseln_auf_fremdes_modell_abgelehnt_kein_500(env, client, admin_headers):
    pid = _create(client, admin_headers).json()["project_id"]
    r = client.post(f"{B}/projects/{pid}/model", json={"model": "claude-fable-5"}, headers=admin_headers)
    assert r.status_code == 400 and r.json()["detail"]["code"] == "vibe_model_unavailable"


def test_bestehende_agenten_werden_einmal_gebunden(env, client, admin_headers, monkeypatch):
    from backend import model_choice, routes, state
    from hydrahive.agents import config as agent_config
    real = model_choice.template_or_none
    monkeypatch.setattr(model_choice, "template_or_none", lambda: None)
    monkeypatch.setattr(routes, "_default_model", lambda: _chain()[0])
    pid = _create(client, admin_headers).json()["project_id"]          # alt: ohne Template angelegt
    aid = state.get_row(pid)["agent_id"]
    assert not agent_config.get(aid).get("template")
    monkeypatch.setattr(model_choice, "template_or_none", real)
    assert model_choice.bind_existing("vibe") == 1
    assert agent_config.get(aid)["template"] == "modul-schnell"
    assert model_choice.bind_existing("vibe") == 0                       # idempotent
