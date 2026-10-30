"""Hydra-Labor L1 Schritt 4c: Schnittstellen /api/modules/hydralabor – nur Admins, Aufträge im Hintergrund."""
from __future__ import annotations

import pytest
from backend import jobs, state

B = "/api/modules/hydralabor"
MODEL = "claude-sonnet-4-6"


@pytest.fixture
def clean(db_ready):
    state.clear()
    yield
    state.clear()


@pytest.fixture
def started(monkeypatch):
    """jobs.start mitschreiben statt wirklich anlegen."""
    calls = []

    def fake_start(name):
        calls.append(name)
        return state.begin(name)
    monkeypatch.setattr(jobs, "start", fake_start)
    return calls


@pytest.mark.parametrize(("method", "path"), [("get", "/state"), ("post", "/checks"), ("post", "/create"),
                                              ("post", "/reset"), ("post", "/probe"), ("post", "/test"),
                                              ("post", "/remove"), ("post", "/start"), ("post", "/stop")])
def test_nur_admins(client, user_headers, clean, method, path):
    r = getattr(client, method)(B + path, headers=user_headers, json={})
    assert r.status_code == 403


def test_ohne_anmeldung(client, clean):
    assert client.get(B + "/state").status_code == 401


def test_zustand_ohne_interna(client, admin_headers, clean):
    state.mark_made("project", project_id="p1", agent_id="a1")
    r = client.get(B + "/state", headers=admin_headers)
    assert r.status_code == 200
    d = r.json()
    assert d["step"] == "start" and d["running"] == "" and d["project_id"] == "p1" and d["agent_id"] == "a1"
    assert (d["cpu"], d["ram_mb"], d["disk_gb"]) == (2, 4096, 20)
    assert "made" not in d and "admin" not in d


def test_voraussetzungen(client, admin_headers, clean, monkeypatch):
    from backend import checks

    async def fake(*, disk_gb, ram_mb):
        return {"ok": True, "checks": [{"id": "core", "ok": True, "code": "", "have": None, "need": None}],
                "args": [disk_gb, ram_mb]}
    monkeypatch.setattr(checks, "run", fake)
    r = client.post(B + "/checks", headers=admin_headers, json={"disk_gb": 30, "ram_mb": 8192})
    assert r.status_code == 200 and r.json()["args"] == [30, 8192]


def test_anlegen_speichert_wahl_und_startet(client, admin_headers, clean, started, monkeypatch):
    from hydrahive.agents import _validation
    monkeypatch.setattr(_validation, "_available_models", lambda: {MODEL})
    r = client.post(B + "/create", headers=admin_headers,
                    json={"model": MODEL, "cpu": 3, "ram_mb": 6144, "disk_gb": 30})
    assert r.status_code == 202 and started == ["create"]
    s = state.get()
    assert (s["model"], s["cpu"], s["ram_mb"], s["disk_gb"], s["admin"]) == (MODEL, 3, 6144, 30, "boss")


@pytest.mark.parametrize("body", [{"model": MODEL, "cpu": 0}, {"model": MODEL, "ram_mb": 512},
                                  {"model": MODEL, "disk_gb": 5000}, {"model": ""}, {},
                                  {"model": MODEL, "cpu": 2, "extra": 1}])
def test_anlegen_ungueltig(client, admin_headers, clean, started, body):
    r = client.post(B + "/create", headers=admin_headers, json=body)
    assert r.status_code in (400, 422) and started == []


def test_anlegen_unbekanntes_modell(client, admin_headers, clean, started, monkeypatch):
    from hydrahive.agents import _validation
    monkeypatch.setattr(_validation, "_available_models", lambda: {MODEL})
    r = client.post(B + "/create", headers=admin_headers, json={"model": "gibt-es-nicht"})
    assert r.status_code == 400 and r.json()["detail"]["code"] == "labor_model_unavailable" and started == []


def test_anlegen_wenn_schon_fertig(client, admin_headers, clean, started):
    state.set_step("ready")
    r = client.post(B + "/create", headers=admin_headers, json={"model": MODEL})
    assert r.status_code == 409 and r.json()["detail"]["code"] == "labor_already_ready" and started == []


@pytest.mark.parametrize("job", ["reset", "probe", "test", "start", "stop"])
def test_labor_aufraege_nur_wenn_fertig(client, admin_headers, clean, started, job):
    r = client.post(f"{B}/{job}", headers=admin_headers, json={})
    assert r.status_code == 409 and r.json()["detail"]["code"] == "labor_not_ready" and started == []


@pytest.mark.parametrize("job", ["reset", "probe", "test"])
def test_labor_auftraege_starten(client, admin_headers, clean, started, job):
    state.set_step("ready")
    r = client.post(f"{B}/{job}", headers=admin_headers, json={})
    assert r.status_code == 202 and started == [job]


def test_schon_ein_auftrag(client, admin_headers, clean, started):
    state.set_step("ready")
    state.begin("test")
    r = client.post(f"{B}/reset", headers=admin_headers, json={})
    assert r.status_code == 409 and r.json()["detail"]["code"] == "labor_busy"


def test_entfernen_braucht_bestaetigung(client, admin_headers, clean, started):
    state.set_step("ready")
    assert client.post(f"{B}/remove", headers=admin_headers, json={"confirm": "labor"}).status_code == 400
    assert client.post(f"{B}/remove", headers=admin_headers, json={}).status_code == 422
    assert started == []
    r = client.post(f"{B}/remove", headers=admin_headers, json={"confirm": "LABOR"})
    assert r.status_code == 202 and started == ["remove"]


def test_entfernen_geht_auch_nach_fehlschlag(client, admin_headers, clean, started):
    """Halbes Labor (step start, aber Teile da) lässt sich trotzdem entfernen."""
    state.mark_made("network")
    r = client.post(f"{B}/remove", headers=admin_headers, json={"confirm": "LABOR"})
    assert r.status_code == 202 and started == ["remove"]


def test_zuruecksetzen_braucht_kein_wort_aber_dialog(client, admin_headers, clean, started):
    state.set_step("ready")
    assert client.post(f"{B}/reset", headers=admin_headers, json={"confirm": True}).status_code == 202


def test_starten_und_stoppen(client, admin_headers, clean, monkeypatch):
    from backend import container
    calls = []

    async def fake_start():
        calls.append("start")

    async def fake_stop():
        calls.append("stop")
    monkeypatch.setattr(container, "start", fake_start)
    monkeypatch.setattr(container, "stop", fake_stop)
    state.set_step("ready")
    assert client.post(f"{B}/stop", headers=admin_headers, json={}).status_code == 200
    assert client.post(f"{B}/start", headers=admin_headers, json={}).status_code == 200
    assert calls == ["stop", "start"]


def test_zustand_laufend_aus_incus(client, admin_headers, clean, fake_incus):
    state.set_step("ready")
    fake_incus.containers["hh-labor"] = {"args": [], "running": True}
    assert client.get(B + "/state", headers=admin_headers).json()["container_running"] is True
    fake_incus.containers["hh-labor"]["running"] = False
    assert client.get(B + "/state", headers=admin_headers).json()["container_running"] is False


def test_modelle_nur_chat(client, admin_headers, clean, monkeypatch):
    from hydrahive.llm import registry

    async def fake(modality=None):
        assert modality == "chat"
        return [registry.ModelEntry(id="a/m1", provider="a", label="M1", purposes=frozenset({"chat"}))]
    monkeypatch.setattr(registry, "list_models", fake)
    r = client.get(B + "/models", headers=admin_headers)
    assert r.status_code == 200 and r.json() == {"items": [{"id": "a/m1", "label": "M1", "provider": "a"}]}
