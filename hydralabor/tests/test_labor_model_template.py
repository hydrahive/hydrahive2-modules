"""Labor-Agent über das Agenten-Template `labor` (Hydra-Labor 0.4.0, Kern E5)."""
from __future__ import annotations

import pytest
from backend import model_choice, state

B = "/api/modules/hydralabor"


@pytest.fixture
def clean(db_ready):
    state.clear()
    yield
    state.clear()


@pytest.fixture
def started(monkeypatch):
    from backend import jobs
    calls = []

    def fake_start(name):
        calls.append(name)
        return state.begin(name)
    monkeypatch.setattr(jobs, "start", fake_start)
    return calls


def _primary():
    from hydrahive.agents import templates as tpl
    t = tpl.get("labor") or tpl.get("modul-schnell")
    return t["chain"][0]


def test_manifest_bringt_template_labor_mit():
    import json
    from pathlib import Path
    m = json.loads((Path(__file__).resolve().parents[1] / "manifest.json").read_text())
    assert m["templates"] == [{"id": "labor", "label": "Hydra-Labor", "base": "modul-schnell"}]


def test_liste_zeigt_nur_primaer(client, admin_headers, clean):
    r = client.get(B + "/models", headers=admin_headers).json()
    assert [i["id"] for i in r["items"]] == [_primary()]


def test_anlegen_mit_fremdem_modell_abgelehnt(client, admin_headers, clean, started):
    r = client.post(B + "/create", headers=admin_headers, json={"model": "claude-fable-5"})
    assert r.status_code == 400 and r.json()["detail"]["code"] == "labor_model_unavailable" and started == []


def test_anlegen_mit_primaer(client, admin_headers, clean, started):
    r = client.post(B + "/create", headers=admin_headers, json={"model": _primary()})
    assert r.status_code == 202 and started == ["create"]


def test_vorhandener_agent_wird_einmal_gebunden(setup_test_env, monkeypatch):
    from hydrahive.agents import config as agent_config
    a = agent_config.create("project", "Labor-Agent", _primary(), temperature=1.0, max_tokens=16000,
                            thinking_budget=0, owner="boss", created_by="boss")
    assert not a.get("template")
    assert model_choice.bind_existing(a["id"], "hydralabor") is True
    assert agent_config.get(a["id"])["template"] in ("labor", "modul-schnell")
    assert model_choice.bind_existing(a["id"], "hydralabor") is False
