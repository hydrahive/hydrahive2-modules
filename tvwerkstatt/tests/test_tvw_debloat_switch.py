"""Entrümpeln Teil 2 (backend/debloat_switch.py): Namen prüfen, Schutz am Gerät, Schübe, Rücklesen. Ohne Fernseher."""
from __future__ import annotations

import pytest
from backend import debloat_switch as SW
from backend import guard

GTV = "com.google.android.apps.tv.launcherx"
S = "192.168.178.201:5555"


def test_clean_lehnt_gesperrtes_und_unsinn_ab():
    assert SW.clean(["com.tcl.logkit", "com.tcl.logkit", "com.tcl.exhibit"], GTV) == ["com.tcl.logkit", "com.tcl.exhibit"]
    for bad, code in (("android", "tvw_debloat_locked"), (GTV, "tvw_debloat_locked"), (guard.SETUP, "tvw_debloat_locked"),
                      ("com.android.systemui", "tvw_debloat_locked"), ("x; reboot", "tvw_debloat_bad_package"),
                      ("com.a b", "tvw_debloat_bad_package")):
        with pytest.raises(SW.TvwDebloatError) as e:
            SW.clean([bad], GTV)
        assert e.value.code == code, bad
    with pytest.raises(SW.TvwDebloatError):
        SW.clean([], GTV)
    with pytest.raises(SW.TvwDebloatError):
        SW.clean([f"com.example.p{i}" for i in range(SW.MAX_PER_JOB + 1)], GTV)


def test_schutzpruefung_liest_nur():
    s = SW.guard_script(S, ["com.tcl.logkit"])
    for verb in ("disable", "pm enable", "uninstall", "settings put", "set-home"):
        assert verb not in s, verb
    assert "TV_INPUT_HARDWARE" in s and "vnd.android.cursor.item/channel" in s and "android.settings.SETTINGS" in s


def test_blocked_eingaenge_handler_und_nicht_pruefbar():
    out = ("__TVW__ state=device\n__TVW__ hw com.tcl.logkit ok\n__TVW__ hw com.tcl.tvinput hw\n"
           "__TVW__ hw com.tcl.tv ok\n__TVW__ hw com.old.dump nochk\n__TVW__ hw com.x.hung hung\n"
           "__TVW__ handler com.tcl.tv\n__TVW__ handler com.android.tv.settings\n")
    pk = ["com.tcl.logkit", "com.tcl.tvinput", "com.tcl.tv", "com.old.dump", "com.x.hung", "com.fehlt.ganz"]
    assert SW.blocked(out, pk) == {"com.tcl.tvinput": "inputs", "com.tcl.tv": "handler", "com.old.dump": "unchecked",
                                   "com.x.hung": "unchecked", "com.fehlt.ganz": "unchecked"}


def test_blocked_fernseher_weg():
    from backend import install
    with pytest.raises(install.TvwInstallError):
        SW.blocked("__TVW__ state=offline\n", ["com.tcl.logkit"])


def test_schub_skript_nur_disable_user_bzw_enable_nie_uninstall():
    off = SW.switch_script(S, ["com.tcl.logkit", "com.tcl.exhibit"], on=False)
    on = SW.switch_script(S, ["com.tcl.logkit"], on=True)
    assert off.count("pm disable-user --user 0 ") == 2 and "pm enable" not in off
    assert "pm enable --user 0 com.tcl.logkit" in on and "disable-user" not in on
    assert "uninstall" not in off + on
    assert "pm list packages -d" in off and "home=" in off


def test_rueckgelesen():
    out = "__TVW__ state=device\n__TVW__ off com.tcl.logkit\n__TVW__ off kaputt;x\n__TVW__ home=com.gathin.tvhome/.Main\n"
    assert SW.read_back(out) == ({"com.tcl.logkit"}, "com.gathin.tvhome")


def test_schuebe_zu_vier():
    assert [len(b) for b in SW.batches([f"com.e.p{i}" for i in range(10)])] == [4, 4, 2]
