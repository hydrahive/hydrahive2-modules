"""Zusätze (backend/addons.py, addon_build.py): Katalog lesen, Gradle-Prüfung, Skripte, Auswertung. Ohne Fernseher."""
from __future__ import annotations

import io
import tarfile

import pytest
from backend import addon_build as AB
from backend import addons

README = """# Add-ons

| Add-on | What it does | Author | Tested on | Permissions | Screenshot |
|---|---|---|---|---|---|
| [Koi Pond](koi-pond/) | A **pixel** koi pond as a [screensaver](x) | [@someone](https://x) | Sony X | None | <img> |
| [Remote Access](remote-access/) | Whether `ADB` is open | [@maxhayim](https://x) | MOKA | network state | <img> |
"""
KOI_GRADLE = "android { namespace 'io.example.koi'\n defaultConfig { applicationId 'io.example.koi'\n minSdk 26 } }"
RA_GRADLE = 'android { defaultConfig { applicationId = "io.example.remote"; minSdkVersion = 28 } }'
KOI_MANIFEST = ('<manifest><application><service android:name=".Dream" '
                'android:permission="android.permission.BIND_DREAM_SERVICE"><intent-filter><action '
                'android:name="android.service.dreams.DreamService"/></intent-filter></service></application></manifest>')
RA_MANIFEST = ('<manifest><uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />'
               '<uses-permission android:name="android.permission.WRITE_SECURE_SETTINGS" />'
               '<provider android:permission="android.permission.DUMP"/></manifest>')


def tgz(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as t:
        for name, data in files.items():
            ti = tarfile.TarInfo(name)
            ti.size = len(data)
            t.addfile(ti, io.BytesIO(data))
    return buf.getvalue()


BLOB = tgz({"./README.md": README.encode(), "./koi-pond/app/build.gradle": KOI_GRADLE.encode(),
            "./koi-pond/app/src/main/AndroidManifest.xml": KOI_MANIFEST.encode(), "./koi-pond/screenshot.jpg": b"jpg",
            "./remote-access/app/build.gradle.kts": RA_GRADLE.encode(),
            "./remote-access/app/src/main/AndroidManifest.xml": RA_MANIFEST.encode(),
            "./Bad_Name/app/build.gradle": b"applicationId 'x.y'", "./big/app/build.gradle": b"x" * 300_000})


def test_katalog_lesen():
    cat, images = addons.parse(BLOB)
    by = {c["id"]: c for c in cat}
    assert set(by) == {"koi-pond", "remote-access"}
    koi, ra = by["koi-pond"], by["remote-access"]
    assert (koi["name"], koi["package"], koi["min_sdk"], koi["dream"], koi["permissions"]) == (
        "Koi Pond", "io.example.koi", 26, True, [])
    assert koi["what"] == "A pixel koi pond as a screensaver" and koi["author"] == "@someone"
    assert ra["package"] == "io.example.remote" and ra["min_sdk"] == 28 and ra["has_image"] is False
    assert ra["permissions"] == [{"name": "ACCESS_NETWORK_STATE", "level": ""},
                                 {"name": "WRITE_SECURE_SETTINGS", "level": "red"}]  # DUMP schützt nur einen Anbieter
    assert images == {"koi-pond": b"jpg"}


@pytest.mark.parametrize("blob", [b"", b"kaputt", b"x" * (addons.MAX_TAR + 1), tgz({"./README.md": b"nix"})])
def test_katalog_kaputt(blob):
    with pytest.raises(addons.TvwAddonError) as e:
        addons.parse(blob)
    assert e.value.code == "tvw_addons_catalog_failed"


def test_einfacher_text():
    assert addons.plain('<img src="x"> **fett** [Link](u) `code`') == "fett Link code"


def test_ordnername_geprueft():
    assert AB.folder("koi-pond").endswith("/addons/koi-pond")
    for bad in ("../launcher", "Koi", "a;b", "", "x" * 50):
        with pytest.raises(addons.TvwAddonError):
            AB.folder(bad)


def test_gradle_pruefung_gegen_gradle_org():
    s = AB.verify_script("tv-hub")
    for v, (jar, dist) in AB.GRADLE.items():
        assert f"{v})" in s and jar in s and dist in s
    assert "../../launcher/gradle/wrapper" in s and "exit 4" in s


def test_bau_und_installation_ohne_skripte_und_sonderrechte():
    b, i = AB.build_script("koi-pond"), AB.install_script("192.168.178.201:5555", "koi-pond")
    for s in (b, i):
        for bad in ("install.sh", "build-and-install", "pm grant", "appops", "settings put", "am start"):
            assert bad not in s, bad
    assert "assembleRelease" in b and "pm install -r" in i


def test_auswertung():
    vals = {"sha256": "a" * 64, "size": "100", "sdk": "26", "perms": "android.permission.INTERNET,android.permission.X,;x,",
            "badging": "package: name='io.example.koi' versionCode='3' versionName='1.2'"}
    assert AB.evaluate(vals, "io.example.koi") == {"sha256": "a" * 64, "size": 100, "package": "io.example.koi",
                                                  "version": "1.2 (3)", "min_sdk": 26,
                                                  "permissions": ["INTERNET", "X"]}
    with pytest.raises(addons.TvwAddonError) as e:
        AB.evaluate(vals, "io.other")
    assert e.value.code == "tvw_build_unexpected"
    with pytest.raises(addons.TvwAddonError):
        AB.evaluate({**vals, "sha256": "x"}, "io.example.koi")


def test_entfernen_nur_nachinstalliert_nie_startbildschirm():
    s = AB.remove_script("192.168.178.201:5555", "io.example.koi")
    assert s.index("pm list packages -3") < s.index("pm uninstall io.example.koi")
    for bad in ("com.gathin.tvhome", "x;y", ""):
        with pytest.raises(addons.TvwAddonError):
            AB.remove_script("192.168.178.201:5555", bad)
