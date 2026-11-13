"""App-Verwaltung (backend/store.py): Eingaben prüfen, Skripte, Auswertung. Ohne Fernseher."""
from __future__ import annotations

import pytest
from backend import store

S = "192.168.178.201:5555"
GTV = "com.google.android.apps.tv.launcherx"


def test_suchtext_geprueft_und_kodiert():
    assert store.query("Kodi  Media Center") == "Kodi%20Media%20Center"
    assert store.query("Tom & Jerry's +1") == "Tom%20%26%20Jerry%27s%20%2B1"
    assert store.query("Mediathek Ärger") == "Mediathek%20%C3%84rger"
    for bad in ("", "a" * 61, "x; reboot", "q$(id)", "a`b`", "a\"b", "a|b", "a\nb", "<script>"):
        with pytest.raises(store.TvwStoreError):
            store.query(bad)


def test_paketname_geprueft():
    assert store.package("tv.emby.embyatv") == "tv.emby.embyatv"
    for bad in ("emby", "tv.emby;reboot", "tv.emby embyatv", "", None, "a." + "b" * 200):
        with pytest.raises(store.TvwStoreError):
            store.package(bad)


def test_store_aufrufe_fest_an_den_play_store():
    o = store.open_script(S, "tv.emby.embyatv")
    q = store.search_script(S, "Kodi Media")
    assert "market://details?id=tv.emby.embyatv" in o and "market://search?q=Kodi%20Media" in q
    for s in (o, q):
        assert "-p com.android.vending" in s and "android.intent.action.VIEW" in s
        for verb in ("pm ", "uninstall", "settings put", "disable"):
            assert verb not in s, verb


def test_lesen_nur_lesend():
    s = store.list_script(S)
    assert "pm list packages -3" in s
    for verb in ("uninstall", "disable", "pm enable", "am start", "settings put"):
        assert verb not in s, verb


def test_liste_auswerten():
    out = ("__TVW__ state=device\n"
           "__TVW__ app|tv.emby.embyatv|250500|2.5.05g|com.android.vending|0\n"
           "__TVW__ app|com.gathin.tvhome|13|3.4||0\n"
           "__TVW__ app|com.off.app|1|1.0|null|3\n"
           "__TVW__ app|kaputt;x|1|1|x|0\n"
           "__TVW__ app|com.weird.name|abc|<b>|com.android.vending|0\n")
    apps = {a["package"]: a for a in store.parse_list(out)}
    assert set(apps) == {"tv.emby.embyatv", "com.gathin.tvhome", "com.off.app", "com.weird.name"}
    assert apps["tv.emby.embyatv"] == {"package": "tv.emby.embyatv", "version_code": "250500", "version_name": "2.5.05g",
                                       "installer": "com.android.vending", "enabled": True}
    assert apps["com.off.app"]["enabled"] is False and apps["com.gathin.tvhome"]["installer"] == ""
    assert apps["com.weird.name"]["version_code"] == "" and apps["com.weird.name"]["version_name"] == ""


def test_store_start_auswerten():
    store.started("__TVW__ state=device\nStarting: Intent { act=android.intent.action.VIEW }\n"
                  "Warning: Activity not started, intent has been delivered to currently running top-most instance.\n")
    for bad in ("__TVW__ state=device\nError: Activity not started, unable to resolve Intent\n",
                "__TVW__ state=device\nStarting: Intent { }\nError: Activity class does not exist\n"):
        with pytest.raises(store.TvwStoreError):
            store.started(bad)


def test_geschuetzt():
    for p in ("com.gathin.tvhome", GTV, "com.android.vending", "com.android.systemui"):
        assert store.protected(p, GTV), p
    assert not store.protected("tv.emby.embyatv", GTV)


def test_deinstallieren_prueft_auf_dem_geraet_und_liest_zurueck():
    s = store.uninstall_script(S, "tv.emby.embyatv")
    assert s.index("pm list packages -3") < s.index("pm uninstall tv.emby.embyatv")
    assert "not_user" in s and "gone" in s and "disable" not in s
    store.uninstalled("__TVW__ state=device\nSuccess\n__TVW__ gone\n")
    with pytest.raises(store.TvwStoreError) as e:
        store.uninstalled("__TVW__ state=device\n__TVW__ not_user\n")
    assert e.value.code == "tvw_store_not_user_app"
    with pytest.raises(store.TvwStoreError):
        store.uninstalled("__TVW__ state=device\nFailure [DELETE_FAILED_INTERNAL_ERROR]\n__TVW__ still\n")
