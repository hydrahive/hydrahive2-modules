"""Hydra-Labor L1 Schritt 4a: Zustand (eine Zeile je Server) – was das Modul angelegt hat, Fortschritt, Fehler."""
from __future__ import annotations

import pytest
from backend import state


@pytest.fixture
def st(db_ready):
    state.clear()
    yield
    state.clear()


def test_leer_am_anfang(st):
    s = state.get()
    assert s["step"] == "start" and s["made"] == {} and s["running"] == "" and s["error_code"] == ""
    assert (s["cpu"], s["ram_mb"], s["disk_gb"]) == (2, 4096, 20)


def test_merken_was_angelegt_ist(st):
    state.mark_made("network")
    state.mark_made("container")
    state.mark_made("project", project_id="p1", agent_id="a1")
    m = state.get()["made"]
    assert m["network"] is True and m["container"] is True
    assert m["project_id"] == "p1" and m["agent_id"] == "a1"


def test_unbekanntes_teil_abgelehnt(st):
    with pytest.raises(ValueError):
        state.mark_made("irgendwas")


def test_lauf_und_fortschritt(st):
    assert state.begin("create") is True
    assert state.begin("reset") is False                     # nur ein Auftrag gleichzeitig
    state.progress("container")
    s = state.get()
    assert s["running"] == "create" and s["progress"] == "container"
    state.finish(error_code="labor_net_open")
    s = state.get()
    assert s["running"] == "" and s["error_code"] == "labor_net_open" and s["progress"] == ""


def test_neuer_lauf_loescht_alten_fehler(st):
    state.begin("create")
    state.finish(error_code="labor_setup_failed", error_step="node")
    assert state.get()["error_step"] == "node"
    state.begin("create")
    s = state.get()
    assert s["error_code"] == "" and s["error_step"] == ""


def test_einstellungen(st):
    state.save_choice(model="m1", cpu=3, ram_mb=8192, disk_gb=40)
    s = state.get()
    assert (s["model"], s["cpu"], s["ram_mb"], s["disk_gb"]) == ("m1", 3, 8192, 40)


def test_schritt_fertig_und_netzprobe(st):
    state.set_step("ready")
    state.net_ok()
    s = state.get()
    assert s["step"] == "ready" and s["last_net_ok"].endswith("Z")
    with pytest.raises(ValueError):
        state.set_step("kaputt")


def test_unterbrochener_lauf_nach_neustart(st):
    state.begin("create")
    state.recover_after_restart()
    s = state.get()
    assert s["running"] == "" and s["error_code"] == "labor_interrupted"


def test_clear_nur_eigene_zeile(st):
    state.save_choice(model="m1", cpu=2, ram_mb=4096, disk_gb=20)
    state.clear()
    assert state.get()["model"] == ""
