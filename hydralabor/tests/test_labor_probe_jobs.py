"""Hydra-Labor L3: Probe bauen / starten / stoppen (incus + root als Attrappe), Aufräumen bei Entfernen/Zurücksetzen."""
from __future__ import annotations

import asyncio

import pytest
from backend import container, jobs, network, probe, probe_net, probe_site, state

GW = "10.77.0.1"


def run(coro):
    return asyncio.run(coro)


@pytest.fixture
def lab(fake_incus, db_ready, monkeypatch, tmp_path):
    fake_incus.containers["hh-labor"] = {"args": [], "running": True}
    fake_incus.networks["hhlabor0"] = {"ipv4.address": f"{GW}/24"}
    fake_incus.acls["hhlabor-acl"] = {"egress": [], "ingress": []}
    state.clear()
    state.set_step("ready")
    for part in ("network", "container", "setup", "snapshot"):
        state.mark_made(part)
    roots: list[str] = []
    ok = {"v": True}

    def fake_apply(ip, *, root, data_dir):
        roots.append(f"apply {ip} {data_dir}")
        return ok["v"]

    def fake_remove(*, root, data_dir):
        roots.append(f"remove {data_dir}")

    monkeypatch.setattr(probe_site, "apply", fake_apply)
    monkeypatch.setattr(probe_site, "remove", fake_remove)
    monkeypatch.setattr(probe, "_data_dir", lambda: tmp_path)
    fake_incus.roots = roots
    fake_incus.apply_ok = ok
    yield fake_incus
    state.clear()


def _execs(lab):
    return [" ".join(c[c.index("--") + 1:]) for c in lab.calls if c[0] == "exec"]


def _exec_calls(lab):
    return [c for c in lab.calls if c[0] == "exec"]


# --- bauen -----------------------------------------------------------------------------------------------------------

def test_bauen_als_labor_nutzer(lab):
    run(probe.build(report=lambda _k: None))
    build = [c for c in _exec_calls(lab) if "npm run build" in " ".join(c)]
    assert len(build) == 1
    c = build[0]
    assert c[c.index("--user") + 1] == "1000" and c[c.index("--group") + 1] == "1000"
    assert "HOME=/home/labor" in c


def test_bauen_legt_daten_und_schluessel_an(lab):
    run(probe.build(report=lambda _k: None))
    s = " ".join(_execs(lab))
    assert "install -d -m 700 /work/.probe /work/.probe/data /work/.probe/config" in s
    assert "[ -f /work/.probe/env ]" in s                      # nur beim ersten Mal neu
    assert "HH_SECRET_KEY=" in s and "HH_INITIAL_ADMIN_PASSWORD=" in s and "/dev/urandom" in s
    assert "chmod 600 /work/.probe/env" in s


def test_bauen_legt_auslieferer_als_root_hinein(lab):
    run(probe.build(report=lambda _k: None))
    assert len(lab.pushed) == 1
    p = lab.pushed[0]
    assert p[2].endswith("/probe/front.py") and p[3] == "hh-labor/opt/hh-labor-probe/front.py"
    for flag in ("--uid", "--gid"):
        assert p[p.index(flag) + 1] == "0"
    assert p[p.index("--mode") + 1] == "0644" and "--create-dirs" not in p
    # --create-dirs legt den Ordner mit 0750 an → labor kann front.py nicht lesen (Befund hydratest 30.10.)
    mk = [c for c in _exec_calls(lab) if "install -d -m 755 -o root -g root /opt/hh-labor-probe" in " ".join(c)]
    assert len(mk) == 1 and "--user" not in mk[0][:mk[0].index("--")]
    assert lab.calls.index(mk[0]) < lab.calls.index(p)


def test_bauen_fehler(lab):
    lab.exec_answers["npm run build"] = (1, "")
    with pytest.raises(container.LaborError, match="labor_probe_build_failed"):
        run(probe.build(report=lambda _k: None))


def test_bauen_meldet_fortschritt(lab):
    seen = []
    run(probe.build(report=seen.append))
    assert seen == ["probe_build"]


# --- starten ---------------------------------------------------------------------------------------------------------

def test_starten_zwei_dienste_als_labor(lab):
    run(probe.start(report=lambda _k: None))
    s = next(x for x in _execs(lab) if "systemd-run" in x)
    assert s.count("systemd-run") == 3                         # Backend, Auslieferer, Neustart-Wächter
    assert "--unit hh-probe-back --uid 1000 --gid 1000" in s and "--unit hh-probe-front --uid 1000 --gid 1000" in s
    assert "-p EnvironmentFile=/work/.probe/env" in s
    assert "--host 127.0.0.1 --port 8002" in s
    assert "/opt/hh-labor-probe/front.py /work/hydrahive2/frontend/dist http://127.0.0.1:8002 8001" in s
    assert "http://127.0.0.1:8001/api/health" in s


def test_starten_neustart_waechter(lab):
    """Modul installieren/aktualisieren in der Probe fordert einen Neustart an (.restart_request) – auf dem Server
    erledigt das hydrahive2-restart.timer, in der Probe ein eigener Wächter (Befund Till 31.10.)."""
    run(probe.start(report=lambda _k: None))
    s = next(x for x in _execs(lab) if "systemd-run" in x)
    assert ("systemd-run -q --collect --unit hh-probe-restart "
            "--path-property=PathExists=/work/.probe/data/.restart_request") in s
    assert "rm -f /work/.probe/data/.restart_request; systemctl restart hh-probe-back" in s
    assert s.index("--unit hh-probe-restart") > s.index("--unit hh-probe-back")  # erst wenn das Backend läuft
    assert "rm -f /work/.probe/data/.restart_request; systemctl stop hh-probe-restart.path" in s.split(
        "--unit hh-probe-back")[0]                                              # alte Anforderung/alter Wächter weg


def test_starten_eigene_daten_keine_dienste_nach_aussen(lab):
    run(probe.start(report=lambda _k: None))
    s = next(x for x in _execs(lab) if "systemd-run" in x)
    for kv in ("HH_DATA_DIR=/work/.probe/data", "HH_CONFIG_DIR=/work/.probe/config", "HH_BASE_DIR=/work/hydrahive2",
               "HH_DISCORD_ENABLED=0", "HH_WA_ENABLED=0", "HH_MAIL_ENABLED=0", "HH_TEAMCHAT_ENABLED=0",
               "HH_UPDATE_CHECK_ENABLED=0", "HH_AGENTLINK_URL=",
               "HH_MODULE_HUB_GIT_URL=/work/hydrahive2-modules"):
        assert f"-E {kv} " in s or s.endswith(f"-E {kv}")


def test_starten_als_root_im_container_ohne_server_umgebung(lab):
    run(probe.start(report=lambda _k: None))
    c = next(c for c in _exec_calls(lab) if "systemd-run" in " ".join(c))
    assert "--user" not in c[:c.index("--")]                     # systemd-run braucht root im Container
    assert c[:2] == ["exec", "hh-labor"]


def test_starten_oeffnet_port_und_nginx(lab):
    run(probe.start(report=lambda _k: None))
    assert any(r.get("source") == f"{GW}/32" and r.get("destination_port") == "8001"
               for r in lab.acls["hhlabor-acl"]["ingress"])
    assert lab.roots[-1].startswith("apply 10.77.0.5 ")
    assert {"probe_net", "probe_site"} <= set(state.get()["made"])


def test_starten_nginx_fehler(lab):
    lab.apply_ok["v"] = False
    with pytest.raises(container.LaborError, match="labor_probe_nginx_failed"):
        run(probe.start(report=lambda _k: None))
    assert "probe_site" not in state.get()["made"]


def test_starten_ohne_bau(lab):
    lab.exec_answers["systemd-run"] = (3, "")
    with pytest.raises(container.LaborError, match="labor_probe_not_built"):
        run(probe.start(report=lambda _k: None))
    assert not lab.acls["hhlabor-acl"]["ingress"] and not lab.roots


def test_starten_kommt_nicht_hoch(lab):
    lab.exec_answers["systemd-run"] = (4, "")
    with pytest.raises(container.LaborError, match="labor_probe_start_failed"):
        run(probe.start(report=lambda _k: None))
    assert not lab.acls["hhlabor-acl"]["ingress"] and not lab.roots


@pytest.mark.parametrize("ip", ["", "x", "8.8.8.8 (eth0)", "10.77.0.5;rm (eth0)"])
def test_starten_komische_adresse(lab, ip):
    lab.ipv4 = ip
    with pytest.raises(container.LaborError, match="labor_probe_no_address"):
        run(probe.start(report=lambda _k: None))
    assert not lab.roots


def test_starten_zweimal_eine_regel(lab):
    run(probe.start(report=lambda _k: None))
    run(probe.start(report=lambda _k: None))
    assert len(lab.acls["hhlabor-acl"]["ingress"]) == 1


# --- stoppen / aufräumen ---------------------------------------------------------------------------------------------

def test_stoppen_raeumt_alles(lab):
    run(probe.start(report=lambda _k: None))
    run(probe.stop(report=lambda _k: None))
    assert "systemctl stop hh-probe-restart.path hh-probe-front hh-probe-back" in " ".join(_execs(lab))
    assert lab.roots[-1].startswith("remove ")
    assert not lab.acls["hhlabor-acl"]["ingress"]
    assert not ({"probe_net", "probe_site"} & set(state.get()["made"]))


def test_stoppen_haelt_dienste_an_auch_ohne_nginx(lab):
    """Dienste laufen evtl. noch (z. B. nginx-Fehler beim Start) – Stoppen hält sie trotzdem an."""
    run(probe.stop(report=lambda _k: None))
    assert "systemctl stop hh-probe-restart.path hh-probe-front hh-probe-back" in " ".join(_execs(lab))


def test_stoppen_ohne_probe_fasst_nginx_nicht_an(lab):
    run(probe.stop(report=lambda _k: None))
    assert not lab.roots


def test_stoppen_wenn_container_weg(lab):
    run(probe.start(report=lambda _k: None))
    lab.fail["systemctl stop"] = "not running"
    run(probe.stop(report=lambda _k: None))
    assert lab.roots[-1].startswith("remove ")


def test_entfernen_raeumt_nginx(lab):
    run(probe.start(report=lambda _k: None))
    run(jobs.remove(report=lambda _k: None))
    assert any(r.startswith("remove ") for r in lab.roots)


def test_zuruecksetzen_raeumt_nginx(lab, monkeypatch):
    run(probe.start(report=lambda _k: None))

    async def fake_reset():
        return {}
    from backend import provision
    monkeypatch.setattr(provision, "reset", fake_reset)
    run(jobs.reset(report=lambda _k: None))
    assert lab.roots[-1].startswith("remove ")
    assert not lab.acls["hhlabor-acl"]["ingress"]


def test_auftraege_eingetragen():
    for name in ("probe_build", "probe_start", "probe_stop"):
        assert name in jobs.JOBS


# --- Stand ------------------------------------------------------------------------------------------------------------

def test_stand(lab):
    lab.exec_answers["hh-probe-status"] = (0, "built=1\nback=active\nfront=active\npw=Abc_12-xyz\n")
    s = run(probe.status())
    assert s == {"built": True, "running": True, "user": "admin", "password": "Abc_12-xyz", "port": 8443,
                 "open": False}


def test_stand_offen_nur_mit_nginx(lab):
    lab.exec_answers["hh-probe-status"] = (0, "built=1\nback=active\nfront=active\npw=x\n")
    state.mark_made("probe_site")
    assert run(probe.status())["open"] is True


@pytest.mark.parametrize("out,running", [("built=1\nback=active\nfront=inactive\n", False),
                                         ("built=1\nback=failed\nfront=active\n", False),
                                         ("built=0\n", False)])
def test_stand_laeuft_nur_wenn_beide(lab, out, running):
    lab.exec_answers["hh-probe-status"] = (0, out)
    assert run(probe.status())["running"] is running


@pytest.mark.parametrize("pw", ["<script>", "a b", "x" * 101, "ä"])
def test_stand_komisches_passwort_nicht_zeigen(lab, pw):
    lab.exec_answers["hh-probe-status"] = (0, f"built=1\nback=active\nfront=active\npw={pw}\n")
    assert run(probe.status())["password"] == ""


def test_stand_container_aus(lab):
    lab.containers["hh-labor"]["running"] = False
    assert run(probe.status()) == {"built": False, "running": False, "user": "admin", "password": "", "port": 8443,
                                   "open": False}
    assert not _execs(lab)


def test_netz_unveraendert(lab):
    """Die Probe ändert nur die eingehende Regel – ausgehend (Sperre) bleibt wie es ist."""
    lab.acls["hhlabor-acl"]["egress"] = [{"action": "reject", "destination": "10.0.0.0/8"}]
    run(probe.start(report=lambda _k: None))
    run(probe.stop(report=lambda _k: None))
    assert lab.acls["hhlabor-acl"]["egress"] == [{"action": "reject", "destination": "10.0.0.0/8"}]
    assert network.ACL == "hhlabor-acl" and probe_net.PORT == 8001
