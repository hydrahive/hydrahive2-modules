"""Hydra-Labor L1 Schritt 4b: Aufträge (anlegen, zurücksetzen, Netz prüfen, Testlauf, entfernen).

incus = Attrappe, Projekt/Agent = echter Kern in der Testumgebung. Aufträge laufen hier direkt (await), nicht im
Hintergrund – `start()` wird getrennt geprüft.
"""
from __future__ import annotations

import asyncio

import pytest
from backend import container, jobs, lab_project, network, provision, state

MODEL = "claude-sonnet-4-6"


def run(coro):
    return asyncio.run(coro)


@pytest.fixture
def lab(fake_incus, db_ready, monkeypatch):
    from hydrahive.projects import execution
    monkeypatch.setattr(network, "_host_networks", lambda: set())
    monkeypatch.setattr(network, "_host_addresses", lambda: {"192.168.178.2/32"})
    monkeypatch.setattr(container, "_ubuntu_version", lambda: "24.04")
    monkeypatch.setattr(execution, "_container_exists", lambda name: name in fake_incus.containers)
    state.clear()
    state.save_choice(model=MODEL, cpu=2, ram_mb=4096, disk_gb=20, admin="boss")
    yield fake_incus
    made = state.get()["made"]
    lab_project.remove(made)
    state.clear()


def test_anlegen_komplett(lab):
    seen = []
    run(jobs.create(report=seen.append))
    s = state.get()
    assert s["step"] == "ready" and s["error_code"] == "" and s["last_net_ok"]
    assert set(s["made"]) >= {"network", "container", "setup", "snapshot", "project", "project_id", "agent_id"}
    assert seen[:2] == ["network", "container"] and seen[-2:] == ["snapshot", "project"]
    assert "user" in seen and "frontend" in seen
    from hydrahive.projects import config as project_config
    assert project_config.get(s["made"]["project_id"])["created_by"] == "boss"


def test_anlegen_zweimal_nichts_doppelt(lab):
    run(jobs.create(report=lambda _k: None))
    pid = state.get()["made"]["project_id"]
    run(jobs.create(report=lambda _k: None))
    assert state.get()["made"]["project_id"] == pid
    assert sum(1 for c in lab.calls if c[0] == "launch") == 1


def test_anlegen_nach_abbruch_beim_projekt_richtet_nicht_neu_ein(lab, monkeypatch):
    """Container + Einrichtung fertig, Projekt scheiterte → zweiter Lauf macht nur das Projekt (keine 2. Einrichtung)."""
    from backend import container as ct
    state.mark_made("network")
    state.mark_made("container")
    state.mark_made("setup")
    run(network.ensure_network())
    lab.containers["hh-labor"] = {"args": [], "running": True}
    n = len(lab.calls)
    run(jobs.create(report=lambda _k: None))
    later = lab.calls[n:]
    assert not any(c[0] == "launch" for c in later)
    probes = [c for c in later if c[0] == "exec" and "hh-labor-netprobe" in c[-1]]
    assert len(probes) == 0                                         # keine neue Anlege-Probe, kein neues Anlegen
    assert not any(c[0] == "exec" and "useradd" in c[-1] for c in later)
    assert ct.NAME in lab.containers and state.get()["step"] == "ready"


def test_anlegen_scheitert_nur_eigenes_weg(lab):
    lab.networks["hhlabor0"] = {"ipv4.address": "10.77.0.1/24"}        # Netz gab es schon (nicht von diesem Lauf)
    lab.acls["hhlabor-acl"] = {"egress": [], "ingress": []}
    lab.exec_answers["nodesource"] = (1, "")
    with pytest.raises(provision.SetupError):
        run(jobs.create(report=lambda _k: None))
    s = state.get()
    assert s["step"] == "start" and "container" not in s["made"] and "setup" not in s["made"]
    assert "hh-labor" not in lab.containers
    assert "hhlabor0" in lab.networks                                   # nicht von uns → bleibt
    assert s["made"].get("network") is None


def test_anlegen_scheitert_netz_von_diesem_lauf_weg(lab):
    lab.exec_answers["nodesource"] = (1, "")
    with pytest.raises(provision.SetupError):
        run(jobs.create(report=lambda _k: None))
    assert "hhlabor0" not in lab.networks and "hhlabor-acl" not in lab.acls


def test_entfernen_nur_was_angelegt_ist(lab):
    run(jobs.create(report=lambda _k: None))
    made = state.get()["made"]
    run(jobs.remove(report=lambda _k: None))
    from hydrahive.projects import config as project_config
    assert project_config.get(made["project_id"]) is None
    assert "hh-labor" not in lab.containers and "hhlabor0" not in lab.networks
    s = state.get()
    assert s["made"] == {} and s["step"] == "start"


def test_entfernen_ohne_labor_fasst_nichts_an(lab):
    lab.containers["hh-labor"] = {"args": [], "running": True}         # fremder Container gleichen Namens
    lab.networks["hhlabor0"] = {}
    run(jobs.remove(report=lambda _k: None))
    assert "hh-labor" in lab.containers and "hhlabor0" in lab.networks
    assert not any(c[0] == "delete" or c[:2] == ["network", "delete"] for c in lab.calls)


def test_zuruecksetzen_merkt_netzprobe(lab):
    run(jobs.create(report=lambda _k: None))
    state._set(last_net_ok="")
    run(jobs.reset(report=lambda _k: None))
    assert state.get()["last_net_ok"]


def test_netz_pruefen_offen_stoppt_container(lab):
    run(jobs.create(report=lambda _k: None))
    lab.open_targets.add("10.77.0.1:443")
    with pytest.raises(network.LaborNetworkError):
        run(jobs.probe(report=lambda _k: None))
    assert lab.containers["hh-labor"]["running"] is False             # offen → Labor aus


def test_netz_pruefen_gleicht_serveradressen_ab(lab, monkeypatch):
    """Server bekommt eine neue Adresse → Sperrliste wird beim Prüfen nachgezogen."""
    run(jobs.create(report=lambda _k: None))
    monkeypatch.setattr(network, "_host_addresses", lambda: {"192.168.178.2/32", "203.0.113.50/32"})
    run(jobs.probe(report=lambda _k: None))
    rules = lab.acls["hhlabor-acl"]["egress"]
    reject = [r for r in rules if r["action"] == "reject"]
    assert len(reject) == 1 and len(rules) == 2                   # alte Regel weg, keine doppelte
    assert "203.0.113.50/32" in reject[0]["destination"] and "10.0.0.0/8" in reject[0]["destination"]
    n = len(lab.calls)
    run(jobs.probe(report=lambda _k: None))                          # nichts geändert → keine Regel angefasst
    assert not any(c[:4] == ["network", "acl", "rule", "add"] for c in lab.calls[n:])


def test_regel_abgleich_neue_zuerst_dann_alte_weg(lab, monkeypatch):
    run(jobs.create(report=lambda _k: None))
    monkeypatch.setattr(network, "_host_addresses", lambda: {"203.0.113.50/32"})
    n = len(lab.calls)
    assert run(network.sync_rules()) is True
    acts = [c[3] for c in lab.calls[n:] if c[:3] == ["network", "acl", "rule"]]
    assert acts == ["add", "remove"]


SUMMARY = "5241 passed, 11 skipped, 1542 warnings in 274.19s (0:04:34)"


def test_testlauf_zusammenfassung(lab):
    run(jobs.create(report=lambda _k: None))
    lab.exec_answers["pytest -q"] = (0, "....\n" + SUMMARY + "\n")
    run(jobs.test(report=lambda _k: None))
    t = state.get()["last_test"]
    assert t["ok"] is True and t["passed"] == 5241 and t["failed"] == 0 and t["summary"] == SUMMARY
    call = next(c for c in lab.calls if c[0] == "exec" and "pytest -q" in c[-1])
    assert call[call.index("--user") + 1] == "1000"


def test_testlauf_rot(lab):
    run(jobs.create(report=lambda _k: None))
    lab.exec_answers["pytest -q"] = (1, "FAILED core/tests/test_x.py::test_a\n2 failed, 5239 passed in 280.1s\n")
    run(jobs.test(report=lambda _k: None))
    t = state.get()["last_test"]
    assert t["ok"] is False and t["failed"] == 2 and t["passed"] == 5239
    assert t["failures"] == ["core/tests/test_x.py::test_a"]


def test_testlauf_rueckgabe_nicht_null_trotz_gruener_zeile(lab):
    run(jobs.create(report=lambda _k: None))
    lab.exec_answers["pytest -q"] = (137, SUMMARY + "\n")             # z. B. nach der Zeile abgeschossen
    run(jobs.test(report=lambda _k: None))
    assert state.get()["last_test"]["ok"] is False


def test_testlauf_letzte_zusammenfassung_zaehlt():
    out = "3 passed in 1.0s\n...\n1 failed, 2 passed in 2.0s\n"
    assert jobs.parse_test(1, out)["summary"] == "1 failed, 2 passed in 2.0s"


def test_testlauf_ok_braucht_zusammenfassung():
    assert jobs.parse_test(0, "nichts\n")["ok"] is False


@pytest.mark.parametrize("out", ["", "irgendwas\n", "x" * 100000])
def test_testlauf_ohne_zusammenfassung(lab, out):
    run(jobs.create(report=lambda _k: None))
    lab.exec_answers["pytest -q"] = (2, out)
    run(jobs.test(report=lambda _k: None))
    t = state.get()["last_test"]
    assert t["ok"] is False and t["summary"] == "" and len(t["failures"]) <= 20


def test_testlauf_hoechstens_20_fehler(lab):
    run(jobs.create(report=lambda _k: None))
    out = "".join(f"FAILED core/tests/t.py::t{i}\n" for i in range(50)) + "50 failed in 9.0s\n"
    lab.exec_answers["pytest -q"] = (1, out)
    run(jobs.test(report=lambda _k: None))
    assert len(state.get()["last_test"]["failures"]) == 20


# --- Hintergrund ---------------------------------------------------------------------------------------------------

def test_start_fehler_landet_im_zustand(lab):
    lab.exec_answers["nodesource"] = (1, "")
    assert run(_start_and_wait("create")) is True
    s = state.get()
    assert s["running"] == "" and s["error_code"] == "labor_setup_failed" and s["error_step"] == "node"


def test_start_unbekannter_fehler_allgemeiner_code(lab, monkeypatch):
    async def boom(report):
        raise RuntimeError("unerwartet")
    monkeypatch.setitem(jobs.JOBS, "probe", boom)
    run(_start_and_wait("probe"))
    assert state.get()["error_code"] == "labor_failed"


def test_start_nur_einer_gleichzeitig(lab):
    state.begin("create")
    assert jobs.start("reset") is False


def test_start_unbekannter_auftrag(lab):
    with pytest.raises(KeyError):
        jobs.start("rm-rf")


async def _start_and_wait(name):
    ok = jobs.start(name)
    for _ in range(500):
        if not state.get()["running"]:
            break
        await asyncio.sleep(0.01)
    return ok
