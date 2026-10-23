"""M1b: Anmelde-Vorgänge (Geräte-Code) im Speicher – je Nutzer, Takt von Microsoft, einmal verbrauchbar."""
# ruff: noqa: F811 - pytest-Fixtures aus _ms_base
from __future__ import annotations

import pytest
from _ms_base import CID, _ms_state, app_set, clock, err, ms  # noqa: F401


def test_ohne_app_kein_start(ms, clock):
    from backend import ms_flows
    with pytest.raises(ms_flows.NotConfigured):
        ms_flows.start("alice")
    assert ms.calls == []


def test_start_gibt_kein_device_code_heraus(ms, clock, app_set):
    from backend import ms_flows
    f = ms_flows.start("alice")
    assert set(f) == {"flow_id", "user_code", "verification_uri", "expires_in", "interval"}
    assert f["user_code"] == "ABCD-EFGH" and len(f["flow_id"]) >= 20 and "DEV-geheim" not in str(f)


def test_fremder_nutzer_sieht_vorgang_nicht(ms, clock, app_set):
    from backend import ms_flows
    f = ms_flows.start("alice")
    assert ms_flows.status("bob", f["flow_id"]) is None
    with pytest.raises(ms_flows.FlowError):
        ms_flows.take("bob", f["flow_id"])


def test_takt_wird_eingehalten(ms, clock, app_set):
    """Microsoft verlangt Abstand (interval); zu frühes Fragen schickt nichts zu Microsoft."""
    from backend import ms_flows
    f = ms_flows.start("alice")
    ms.token += [err("authorization_pending"), err("slow_down"), err("authorization_pending")]
    assert ms_flows.status("alice", f["flow_id"]) == {"state": "pending"}
    assert ms.paths().count("login.microsoftonline.com/common/oauth2/v2.0/token") == 0, "erst nach 5 s"
    clock["now"] += 5
    assert ms_flows.status("alice", f["flow_id"]) == {"state": "pending"}
    clock["now"] += 5
    assert ms_flows.status("alice", f["flow_id"]) == {"state": "pending"}      # slow_down → +5 s
    clock["now"] += 5
    ms_flows.status("alice", f["flow_id"])
    assert sum(p.endswith("/token") for p in ms.paths()) == 2, "nach slow_down 10 s Abstand"
    clock["now"] += 5
    ms_flows.status("alice", f["flow_id"])
    assert sum(p.endswith("/token") for p in ms.paths()) == 3


def test_fertig_und_einmal_verbrauchbar(ms, clock, app_set):
    from backend import ms_flows
    f = ms_flows.start("alice")
    clock["now"] += 5
    assert ms_flows.status("alice", f["flow_id"]) == {"state": "done"}
    t = ms_flows.take("alice", f["flow_id"])
    assert t["refresh_token"] == "RT-1" and t["access_token"] == "AT-1"
    with pytest.raises(ms_flows.FlowError):
        ms_flows.take("alice", f["flow_id"])
    assert ms_flows.status("alice", f["flow_id"]) is None


def test_noch_nicht_fertig_nicht_nehmbar(ms, clock, app_set):
    from backend import ms_flows
    f = ms_flows.start("alice")
    with pytest.raises(ms_flows.FlowError):
        ms_flows.take("alice", f["flow_id"])


def test_abgelaufen_ohne_microsoft(ms, clock, app_set):
    from backend import ms_flows
    f = ms_flows.start("alice")
    clock["now"] += 901
    assert ms_flows.status("alice", f["flow_id"]) == {"state": "expired"}
    assert not any(p.endswith("/token") for p in ms.paths())


@pytest.mark.parametrize("code,state", [("access_denied", "denied"), ("authorization_declined", "denied"),
                                        ("expired_token", "expired"), ("invalid_client", "error")])
def test_endzustaende(ms, clock, app_set, code, state):
    from backend import ms_flows
    f = ms_flows.start("alice")
    ms.token.append(err(code, "AADSTS1: kaputt"))
    clock["now"] += 5
    st = ms_flows.status("alice", f["flow_id"])
    assert st["state"] == state
    clock["now"] += 5
    assert ms_flows.status("alice", f["flow_id"])["state"] == state, "Endzustand bleibt, kein neuer Versuch"
    assert sum(p.endswith("/token") for p in ms.paths()) == 1


def test_netzfehler_bleibt_wartend(ms, clock, app_set):
    from backend import ms_flows
    f = ms_flows.start("alice")
    ms.fail_network = True
    clock["now"] += 5
    assert ms_flows.status("alice", f["flow_id"]) == {"state": "pending"}


def test_hoechstens_fuenf_offene_je_nutzer(ms, clock, app_set):
    from backend import ms_flows
    ids = [ms_flows.start("alice")["flow_id"] for _ in range(5)]
    with pytest.raises(ms_flows.TooMany):
        ms_flows.start("alice")
    ms_flows.start("bob")
    clock["now"] += 901
    ms_flows.start("alice")                     # abgelaufene zählen nicht mehr
    assert ms_flows.status("alice", ids[0]) == {"state": "expired"}, "Ende noch eine Weile abrufbar"
    clock["now"] += ms_flows.KEEP_DONE
    assert ms_flows.status("alice", ids[0]) is None, "danach aufgeräumt"


def test_app_gewechselt_vorgang_ungueltig(ms, clock, app_set):
    """Ändert der Admin die Client-ID, gehört ein offener Vorgang zur alten App → nicht mehr verwenden."""
    from backend import ms_app, ms_flows
    f = ms_flows.start("alice")
    ms_app.save("99999999-2222-3333-4444-555555555555", "common")
    clock["now"] += 5
    assert ms_flows.status("alice", f["flow_id"])["state"] == "error"
    assert not any(p.endswith("/token") for p in ms.paths())
