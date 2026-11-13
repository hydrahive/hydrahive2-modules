"""Baustein 6: Skripte zum Aufspielen und Zurück (rein) – Reihenfolge, nur abschalten, Auswertung."""
from __future__ import annotations

import pytest
from backend import install

SERIAL = "192.168.178.200:5555"
STOCK = "com.google.android.tvlauncher"


def test_nur_bekannte_originale():
    assert install.stock(STOCK) == STOCK
    for bad in ("", "com.example.fremd", "android", "com.google.android.tvlauncher; reboot"):
        with pytest.raises(install.TvwInstallError) as e:
            install.stock(bad)
        assert e.value.code == "tvw_no_stock_home"


def test_nie_deinstallieren_nie_debugging_einschalten():
    alles = " ".join((install.push_script(SERIAL), install.start_script(SERIAL), install.switch_script(SERIAL, STOCK),
                      install.restore_script(SERIAL, STOCK)))
    for verboten in ("pm uninstall", "pm clear", "reboot", "adb_enabled 1", "tcpip", "rm -rf"):
        assert verboten not in alles, verboten


def test_umschalten_reihenfolge_original_erst_nach_start():
    """Original erst abschalten, wenn der neue Startbildschirm gestartet ist (eigener Schritt davor), dann Home setzen."""
    s = install.switch_script(SERIAL, STOCK)
    assert s.index(f"pm disable-user --user 0 {STOCK}") < s.index("set-home-activity --user 0 com.gathin.tvhome")
    assert s.index("set-home-activity") < s.index("__TVW__ home=")
    assert "pm revoke com.gathin.tvhome android.permission.WRITE_SECURE_SETTINGS" in s
    assert "am start" not in s and "am start -W" in install.start_script(SERIAL)


def test_zurueck_schaltet_original_ein_und_liest_home():
    s = install.restore_script(SERIAL, STOCK)
    assert s.index(f"pm enable --user 0 {STOCK}") < s.index("set-home-activity")
    assert "disable" not in s and "__TVW__ home=" in s


def test_ohne_freigabe_kein_befehl():
    for s in (install.push_script(SERIAL), install.switch_script(SERIAL, STOCK), install.restore_script(SERIAL, STOCK)):
        assert s.index('[ "$st" = device ] || exit 0') < s.index(" shell ")


@pytest.mark.parametrize("out,code", [("__TVW__ state=unauthorized\n", "tvw_adb_unauthorized"),
                                      ("__TVW__ state=offline\n", "tvw_adb_closed"), ("", "tvw_adb_closed")])
def test_verbindung(out, code):
    with pytest.raises(install.TvwInstallError) as e:
        install.require_open(out)
    assert e.value.code == code


def test_aufspielen_auswertung():
    install.check_installed("__TVW__ state=device\nPerforming Streamed Install\nSuccess\n")
    with pytest.raises(install.TvwInstallError) as e:
        install.check_installed("__TVW__ state=device\nFailure [INSTALL_FAILED_UPDATE_INCOMPATIBLE: signatures]\n")
    assert (e.value.code, e.value.detail) == ("tvw_install_failed", "INSTALL_FAILED_UPDATE_INCOMPATIBLE")


def test_start_auswertung():
    install.check_started("__TVW__ state=device\nStatus: ok\nActivity: com.gathin.tvhome/.MainActivity\nComplete\n")
    for bad in ("__TVW__ state=device\nStatus: ok\nError: Activity not started\n",
                "__TVW__ state=device\nStatus: timeout\n"):
        with pytest.raises(install.TvwInstallError) as e:
            install.check_started(bad)
        assert e.value.code == "tvw_home_not_started"


@pytest.mark.parametrize("out,pkg", [("__TVW__ home=com.gathin.tvhome/.MainActivity", "com.gathin.tvhome"),
                                     ("__TVW__ home=com.google.android.tvlauncher/.MainActivity", STOCK),
                                     ("__TVW__ home=android", ""), ("__TVW__ home=", ""), ("nichts", "")])
def test_home_lesen(out, pkg):
    assert install.home_of(out) == pkg
