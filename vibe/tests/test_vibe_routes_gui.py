"""Die Schnittstellen, die die Oberfläche braucht – so klein wie möglich: anlegen, löschen, Chat öffnen, Versionen, Zurück.

Alles nur für Admins, alles nur für eigene Projekte. Fehler kommen als Code (`vibe_…`), nie als Text mit Pfaden.
"""
from __future__ import annotations

import asyncio

import pytest
from backend import container, jobs, network, provision, state

B = "/api/modules/vibe"
MODEL = "claude-sonnet-4-6"


def run(coro):
    return asyncio.run(coro)


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


def _create(client, admin_headers, name="Meine App"):
    return client.post(B + "/projects", json={"name": name}, headers=admin_headers)


# --- Neues Projekt ---------------------------------------------------------------------------------------------

def test_anlegen_nur_fuer_admins(env, client, user_headers):
    assert client.post(B + "/projects", json={"name": "x"}, headers=user_headers).status_code == 403


def test_anlegen_ohne_anmeldung(env, client):
    assert client.post(B + "/projects", json={"name": "x"}).status_code in (401, 403)


def test_anlegen_gibt_sofort_antwort_und_richtet_im_hintergrund_ein(env, client, admin_headers):
    r = _create(client, admin_headers)
    assert r.status_code == 202 and r.json()["project_id"]
    row = client.get(B + "/state", headers=admin_headers).json()["projects"][0]
    assert row["name"] == "Meine App" and row["state"] in ("new", "setting_up", "ready")


def test_anlegen_modell_kommt_vom_system_nicht_vom_nutzer(env, client, admin_headers, monkeypatch):
    seen = {}

    async def spy(*, admin, name, model, limits=None):
        seen["model"] = model
        return {"project_id": "p", "agent_id": "a"}
    monkeypatch.setattr(jobs, "create_and_setup", spy)
    client.post(B + "/projects", json={"name": "x", "model": "openrouter/teuer"}, headers=admin_headers)
    assert seen["model"] != "openrouter/teuer" and not seen["model"].startswith("openrouter/")


def test_anlegen_ohne_name_ist_ein_fehlercode(env, client, admin_headers):
    r = client.post(B + "/projects", json={"name": "   "}, headers=admin_headers)
    assert r.status_code == 422 or r.json().get("detail", {}).get("code", "").startswith("vibe_")


def test_anlegen_unbekannter_name_zu_lang(env, client, admin_headers):
    assert client.post(B + "/projects", json={"name": "x" * 500}, headers=admin_headers).status_code in (400, 422)


# --- Löschen -----------------------------------------------------------------------------------------------------

def test_loeschen_entfernt_das_projekt(env, client, admin_headers):
    pid = _create(client, admin_headers).json()["project_id"]
    import time
    for _ in range(50):
        if client.get(B + "/state", headers=admin_headers).json()["projects"][0]["state"] == "ready":
            break
        time.sleep(0.1)
    r = client.delete(f"{B}/projects/{pid}", headers=admin_headers)
    assert r.status_code == 200
    assert client.get(B + "/state", headers=admin_headers).json()["projects"] == []


def test_loeschen_fremdes_projekt_gibt_nicht_gefunden(env, client, admin_headers):
    r = client.delete(f"{B}/projects/01a1-gibtsnicht", headers=admin_headers)
    assert r.status_code == 404 and r.json()["detail"]["code"] == "vibe_project_not_found"


def test_loeschen_nur_admin(env, client, user_headers):
    assert client.delete(f"{B}/projects/x", headers=user_headers).status_code == 403


# --- Chat öffnen -----------------------------------------------------------------------------------------------

def test_chat_gibt_sitzung_und_agent_zurueck(env, client, admin_headers):
    pid = _create(client, admin_headers).json()["project_id"]
    r = client.post(f"{B}/projects/{pid}/chat", json={}, headers=admin_headers)
    assert r.status_code == 200 and r.json()["session_id"] and r.json()["agent_id"]


def test_chat_zweimal_gibt_dieselbe_sitzung(env, client, admin_headers):
    pid = _create(client, admin_headers).json()["project_id"]
    a = client.post(f"{B}/projects/{pid}/chat", json={}, headers=admin_headers).json()
    b = client.post(f"{B}/projects/{pid}/chat", json={}, headers=admin_headers).json()
    assert a["session_id"] == b["session_id"]


def test_chat_sitzung_ist_fuer_vibe_markiert_und_weckt_den_container(env, client, admin_headers):
    from hydrahive.db import sessions as sdb
    pid = _create(client, admin_headers).json()["project_id"]
    r = client.post(f"{B}/projects/{pid}/chat", json={}, headers=admin_headers).json()
    assert sdb.get(r["session_id"]).metadata.get("embedded_in") == "vibe"


def test_chat_fremdes_projekt_nicht_gefunden(env, client, admin_headers):
    r = client.post(f"{B}/projects/01a1-gibtsnicht/chat", json={}, headers=admin_headers)
    assert r.status_code == 404


def test_chat_nur_wenn_das_projekt_bereit_ist(env, client, admin_headers):
    pid = _create(client, admin_headers).json()["project_id"]
    state.set_state(pid, "failed", error_code="vibe_setup_failed", error_step="deps")
    r = client.post(f"{B}/projects/{pid}/chat", json={}, headers=admin_headers)
    assert r.status_code == 409 and r.json()["detail"]["code"] == "vibe_not_ready"


# --- Zeitmaschine: sehen und zurück -------------------------------------------------------------------------------

def test_versionen_liste_in_klartext(env, client, admin_headers, monkeypatch):
    from backend import versions
    pid = _create(client, admin_headers).json()["project_id"]

    async def hist(p, limit=200):
        return [{"commit_id": "a" * 40, "summary": "Überschrift geändert", "created_at": "2026-11-05T10:00:00Z"}]
    monkeypatch.setattr(versions, "history", hist)
    r = client.get(f"{B}/projects/{pid}/versions", headers=admin_headers)
    assert r.status_code == 200 and r.json()["versions"][0]["summary"] == "Überschrift geändert"


def test_zurueck_ruft_restore_und_meldet_ergebnis(env, client, admin_headers, monkeypatch):
    from backend import versions
    pid = _create(client, admin_headers).json()["project_id"]
    got = {}

    async def restore(p, sha):
        got["sha"] = sha
        return {"commit_id": "b" * 40, "summary": "Zurück", "kind": "restore", "created_at": "x"}
    monkeypatch.setattr(versions, "restore", restore)
    r = client.post(f"{B}/projects/{pid}/versions/{'a' * 40}/restore", json={}, headers=admin_headers)
    assert r.status_code == 200 and got["sha"] == "a" * 40


def test_zurueck_mit_ungueltiger_version_ist_ein_fehlercode(env, client, admin_headers):
    pid = _create(client, admin_headers).json()["project_id"]
    r = client.post(f"{B}/projects/{pid}/versions/nicht-gueltig/restore", json={}, headers=admin_headers)
    assert r.status_code in (400, 404, 422)


def test_versionen_fremdes_projekt_nicht_gefunden(env, client, admin_headers):
    assert client.get(f"{B}/projects/01a1-gibtsnicht/versions", headers=admin_headers).status_code == 404


def test_versionen_nur_admin(env, client, user_headers):
    assert client.get(f"{B}/projects/x/versions", headers=user_headers).status_code == 403


# --- Nochmal versuchen / Heilung an-aus -------------------------------------------------------------------------

def test_nochmal_versuchen_nur_bei_failed(env, client, admin_headers):
    pid = _create(client, admin_headers).json()["project_id"]
    import time
    for _ in range(50):
        if client.get(B + "/state", headers=admin_headers).json()["projects"][0]["state"] == "ready":
            break
        time.sleep(0.1)
    r = client.post(f"{B}/projects/{pid}/retry", json={}, headers=admin_headers)
    assert r.status_code == 409 and r.json()["detail"]["code"] == "vibe_not_failed"


def test_heilung_schalter_setzen(env, client, admin_headers):
    pid = _create(client, admin_headers).json()["project_id"]
    r = client.post(f"{B}/projects/{pid}/heal", json={"enabled": False}, headers=admin_headers)
    assert r.status_code == 200 and state.get_row(pid)["heal_enabled"] is False
