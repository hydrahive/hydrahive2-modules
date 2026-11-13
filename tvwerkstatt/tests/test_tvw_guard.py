"""Vorprüfung Google TV (backend/guard.py): Einrichtungs-Helfer vor dem Original abschalten, WLAN-Schutz."""
from __future__ import annotations

import pytest
from backend import guard, install

GTV = "com.google.android.apps.tv.launcherx"
S = "192.168.178.201:5555"


def out(claims="", owners="", none="0", home=f"{GTV}/.home.HomeActivity", state="device") -> str:
    return (f"__TVW__ state={state}\n__TVW__ claims={claims}\n__TVW__ wifi_owners={owners}\n"
            f"__TVW__ wifi_none={none}\n__TVW__ home={home}\n")


TCL = f"{GTV},{guard.SETUP},com.android.tv.settings,"


def test_sony_ohne_helfer_nichts_zu_tun():
    sony = out(claims="com.gathin.tvhome,com.android.tv.settings,", home="com.google.android.tvlauncher/.MainActivity")
    assert guard.plan(sony, "com.google.android.tvlauncher") == []


def test_tcl_am_kabel_wlan_gehoert_den_einstellungen():
    assert guard.plan(out(claims=TCL, owners="com.android.tv.settings,"), GTV) == [guard.SETUP]


def test_ohne_gespeichertes_wlan():
    assert guard.plan(out(claims=TCL, none="1"), GTV) == [guard.SETUP]


def test_wlan_gehoert_dem_helfer_nichts_umstellen():
    with pytest.raises(install.TvwInstallError) as e:
        guard.plan(out(claims=TCL, owners=f"com.android.tv.settings,{guard.SETUP},"), GTV)
    assert e.value.code == "tvw_wifi_owned_by_setup"


def test_wlan_nicht_lesbar_nichts_umstellen():
    with pytest.raises(install.TvwInstallError) as e:
        guard.plan(out(claims=TCL), GTV)
    assert e.value.code == "tvw_wifi_unreadable"


def test_original_ist_nicht_mehr_home_nichts_umstellen():
    with pytest.raises(install.TvwInstallError) as e:
        guard.plan(out(claims=TCL, owners="com.android.tv.settings,", home=f"{guard.SETUP}/.RecoveryActivity"), GTV)
    assert e.value.code == "tvw_guard_failed"


@pytest.mark.parametrize("state,code", [("offline", "tvw_adb_closed"), ("unauthorized", "tvw_adb_unauthorized")])
def test_fernseher_nicht_erreichbar(state, code):
    with pytest.raises(install.TvwInstallError) as e:
        guard.plan(out(claims=TCL, owners="x.y,", state=state), GTV)
    assert e.value.code == code


def test_lese_skript_aendert_nichts():
    s = guard.read_script(S)
    assert "query-activities" in s and "dumpsys wifi" in s and "list-networks" in s
    for verb in ("disable", "enable", "set-home", "install", "settings put", " rm "):
        assert verb not in s, verb


def test_abschalten_nur_der_helfer_und_zuruecklesen():
    s = guard.disable_script(S, [guard.SETUP])
    assert s.index(f"pm disable-user --user 0 {guard.SETUP}") < s.index("home=")
    with pytest.raises(install.TvwInstallError):
        guard.disable_script(S, [GTV])


def test_gemerkte_abschaltungen_nur_bekannte():
    assert guard.extras(f"{guard.SETUP}") == [guard.SETUP]
    assert guard.extras(f"com.evil.app,{guard.SETUP};rm -rf /") == []
    assert guard.extras("") == []


def test_rueckweg_schaltet_helfer_vor_der_home_wahl_ein():
    s = install.restore_script(S, GTV, (guard.SETUP,))
    assert s.index(f"pm enable --user 0 {GTV}") < s.index(f"pm enable --user 0 {guard.SETUP}") < s.index("set-home")
    assert "pm enable --user 0 com.evil" not in install.restore_script(S, GTV, ("com.evil;reboot",))
