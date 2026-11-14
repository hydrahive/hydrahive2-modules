"""G2: HydraHive-App im Container bauen – Quelltext-Paket, Skripte, Auswertung (PLAN-APP.md). Auftrag: _jobs."""
from __future__ import annotations

import io
import tarfile

import pytest
from backend import app_build, source

SHA = "7ce69f976b834d3b" + "0" * 48
SIG = "7676576025d19d8297a575312fbb07d5d9466b6b088c4524458328753ec70547"
COLLECT = (f"__TVW__ sha256={SHA}\n__TVW__ size=20332\n__TVW__ badging=package: name='io.hydrahive.app' "
           f"versionCode='1' versionName='0.1.0' platformBuildVersionName='14'\n__TVW__ signer={SIG}\n"
           f"__TVW__ keystore={SIG}\n__TVW__ perms=android.permission.INTERNET,\n__TVW__ tests=6 0 0\n")


# --- Quelltext-Paket --------------------------------------------------------------------------------------------

def test_quelltext_liegt_im_modul_mit_logik_und_tests():
    names = app_build.source_files()
    assert "app/src/main/AndroidManifest.xml" in names and "app/build.gradle" in names
    assert "app/src/main/java/io/hydrahive/app/Logic.java" in names
    assert "app/src/test/java/io/hydrahive/app/LogicTest.java" in names
    assert not [n for n in names if n.startswith(("build/", "app/build/", ".gradle/")) or n.endswith(".apk")]


def test_paket_ist_reproduzierbar_und_ohne_besitzer():
    blob1, digest1 = app_build.source_tar()
    blob2, digest2 = app_build.source_tar()
    assert blob1 == blob2 and digest1 == digest2 and len(digest1) == 64
    with tarfile.open(fileobj=io.BytesIO(blob1)) as t:
        members = t.getmembers()
    assert all(m.isfile() and m.uid == 0 and m.gid == 0 and m.mtime == 0 and not m.name.startswith(("/", ".."))
               for m in members)
    assert [m.name for m in members] == sorted(m.name for m in members)


def test_stand_aendert_sich_mit_dem_quelltext(monkeypatch, tmp_path):
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "a.txt").write_text("eins")
    monkeypatch.setattr(app_build, "SRC_DIR", tmp_path)
    _, d1 = app_build.source_tar()
    (tmp_path / "app" / "a.txt").write_text("zwei")
    _, d2 = app_build.source_tar()
    assert d1 != d2


def test_symlinks_im_quelltext_werden_nicht_mitgenommen(monkeypatch, tmp_path):
    (tmp_path / "echt.txt").write_text("x")
    (tmp_path / "link.txt").symlink_to("/etc/hostname")
    monkeypatch.setattr(app_build, "SRC_DIR", tmp_path)
    assert app_build.source_files() == ["echt.txt"]


# --- Skripte ------------------------------------------------------------------------------------------------------

def test_bau_nutzt_den_geprueften_wrapper_und_testet_zuerst():
    s = app_build.BUILD_SCRIPT
    assert f"{source.SRC}/launcher/gradlew" in s and "-p " in s
    assert s.index("testReleaseUnitTest") < s.index("assembleRelease")
    assert "--no-daemon" in s and "sudo" not in s


def test_entpacken_nur_in_den_eigenen_ordner():
    s = app_build.UNPACK_SCRIPT
    assert f"rm -rf {app_build.DIR}" in s and f"tar -x -C {app_build.DIR}" in s and "--no-same-owner" in s


# --- Auswertung ---------------------------------------------------------------------------------------------------

def test_auswertung():
    from backend import build
    info = app_build.evaluate(build.parse(COLLECT))
    assert info == {"sha256": SHA, "size": 20332, "package": "io.hydrahive.app", "version": "0.1.0 (1)",
                    "signer": SIG, "permissions": "INTERNET"}


@pytest.mark.parametrize("aenderung, code", [
    (("io.hydrahive.app'", "com.example.boese'"), "tvw_build_unexpected"),
    ((f"keystore={SIG}", "keystore=" + "0" * 64), "tvw_signer_mismatch"),
    (("perms=android.permission.INTERNET,", "perms=android.permission.INTERNET,android.permission.CAMERA,"),
     "tvw_app_build_perms"),
    (("perms=android.permission.INTERNET,", "perms="), "tvw_app_build_perms"),
    (("size=20332", f"size={6 * 1024 * 1024}"), "tvw_app_build_too_large"),
    (("tests=6 0 0", "tests=6 1 0"), "tvw_app_build_tests"),
    (("tests=6 0 0", "tests=0 0 0"), "tvw_app_build_tests"),
    (("__TVW__ tests=6 0 0\n", ""), "tvw_app_build_tests"),
    (("sha256=" + SHA, "sha256=xyz"), "tvw_build_unreadable"),
])
def test_auswertung_lehnt_ab(aenderung, code):
    from backend import build
    with pytest.raises(build.TvwBuildError) as e:
        app_build.evaluate(build.parse(COLLECT.replace(*aenderung)))
    assert e.value.code == code


def test_paket_zeit_ist_null_auch_wenn_dateien_neu_sind(monkeypatch, tmp_path):
    import os
    (tmp_path / "a.txt").write_text("x")
    os.utime(tmp_path / "a.txt", (1_800_000_000, 1_800_000_000))
    monkeypatch.setattr(app_build, "SRC_DIR", tmp_path)
    blob, _ = app_build.source_tar()
    with tarfile.open(fileobj=io.BytesIO(blob)) as t:
        assert [m.mtime for m in t.getmembers()] == [0]
