"""Baustein 5: Fernseher – Eingaben prüfen, adb-Skript, Auswertung (rein, ohne incus)."""
from __future__ import annotations

import pytest
from backend import device

HOST = {"192.168.178.2/32"}
SONY = {"state": "device", "ro.product.model": "BRAVIA 4K UR3", "ro.product.manufacturer": "Sony",
        "ro.build.version.release": "9", "ro.build.version.sdk": "28", "ro.build.display.id": "PTT1.190515.001.S54",
        "home": "com.gathin.tvhome", "has_stock_tv": "package:"}


@pytest.mark.parametrize("name,ok", [("Wohnzimmer", "Wohnzimmer"), ("  TV   Küche ", "TV Küche")])
def test_name(name, ok):
    assert device.clean_name(name) == ok


@pytest.mark.parametrize("name", ["", "   ", "x" * 61, "a\nb", "a\x00b"])
def test_name_ungueltig(name):
    with pytest.raises(device.TvwDeviceError) as e:
        device.clean_name(name)
    assert e.value.code == "tvw_bad_name"


def test_ziel():
    assert device.target("192.168.178.200", 5555, HOST) == "192.168.178.200:5555"


@pytest.mark.parametrize("addr,port", [("8.8.8.8", 5555), ("192.168.178.2", 5555), ("1.2.3.4; rm -rf /", 5555),
                                       ("192.168.178.200", 0), ("192.168.178.200 ", 5555)])
def test_ziel_ungueltig(addr, port):
    with pytest.raises(device.TvwDeviceError) as e:
        device.target(addr, port, HOST)
    assert e.value.code == "tvw_bad_address"


def test_skript_nur_lesend():
    s = device.probe_script("192.168.178.200:5555")
    for verboten in ("pm disable", "pm uninstall", "pm install", "set-home-activity", "settings put", "reboot",
                     "input keyevent", "tcpip", "am start"):
        assert verboten not in s, verboten
    assert "getprop ro.build.version.sdk" in s and "resolve-activity" in s
    assert s.count("192.168.178.200:5555") >= 3


def test_auswertung_sony_mit_unserem_startbildschirm():
    info = device.evaluate(SONY)
    assert info == {"adb_state": "open", "model": "Sony BRAVIA 4K UR3", "android": "9", "sdk": 28,
                    "build": "PTT1.190515.001.S54", "stock_home": "com.google.android.tvlauncher",
                    "current_home": "com.gathin.tvhome", "kind": "android_tv", "too_old": False}


def test_auswertung_google_tv_original():
    info = device.evaluate({**SONY, "home": "com.google.android.apps.tv.launcherx", "ro.build.version.sdk": "34",
                            "has_stock_tv": ""})
    assert (info["stock_home"], info["kind"], info["current_home"]) == (
        "com.google.android.apps.tv.launcherx", "google_tv", "com.google.android.apps.tv.launcherx")


def test_gemerktes_original_bleibt():
    info = device.evaluate({**SONY, "has_stock_tv": ""}, stock_before="com.google.android.tvlauncher")
    assert info["stock_home"] == "com.google.android.tvlauncher"


def test_unbekannter_startbildschirm_wird_nicht_als_original_angenommen():
    info = device.evaluate({**SONY, "home": "com.example.fremd", "has_stock_tv": ""})
    assert (info["stock_home"], info["kind"]) == ("", "")


def test_auswahl_dialog_ist_kein_paket():
    assert device.evaluate({**SONY, "home": "android", "has_stock_tv": ""})["current_home"] == ""


def test_zu_alt():
    assert device.evaluate({**SONY, "ro.build.version.sdk": "25"})["too_old"] is True


@pytest.mark.parametrize("raw,state", [("unauthorized", "unauthorized"), ("error: device unauthorized.", "unauthorized"),
                                       ("error: device '192.168.178.200:5555' not found", "closed"), ("", "closed")])
def test_nicht_offen(raw, state):
    assert device.evaluate({"state": raw}) == {"adb_state": state}


def test_kaputte_ausgabe():
    with pytest.raises(device.TvwDeviceError) as e:
        device.evaluate({})
    assert e.value.code == "tvw_device_probe_failed"
    with pytest.raises(device.TvwDeviceError):
        device.evaluate({**SONY, "ro.build.version.sdk": "neun"})


def test_parse_nimmt_nur_markierte_zeilen():
    out = "connected to x\n__TVW__ state=device\nmüll=1\n__TVW__ ro.product.model=BRAVIA=4K\n"
    assert device.parse(out) == {"state": "device", "ro.product.model": "BRAVIA=4K"}


def test_zustand_aus_der_geraeteliste_nicht_aus_der_letzten_fehlerzeile():
    """Fund am Sony (13.11.): `adb get-state` schreibt bei fehlender Freigabe 4 Zeilen, „unauthorized“ steht in der
    ersten, die letzte ist „Otherwise check for a confirmation dialog…“. Gelesen wird darum die Spalte aus
    `adb devices` für genau diese Adresse."""
    s = device.probe_script("192.168.178.200:5555")
    assert "get-state" not in s
    assert "devices" in s and "192.168.178.200:5555" in s
    devices_out = ("List of devices attached\n192.168.178.200:5555   unauthorized transport_id:1\n"
                   "192.168.178.201:5555   device transport_id:2\n\n")
    assert device.state_from_devices(devices_out, "192.168.178.200:5555") == "unauthorized"
    assert device.state_from_devices(devices_out, "192.168.178.201:5555") == "device"
    assert device.state_from_devices(devices_out, "192.168.178.20:5555") == "offline"
    assert device.state_from_devices("", "192.168.178.200:5555") == "offline"
