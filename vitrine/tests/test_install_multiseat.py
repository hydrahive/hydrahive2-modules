"""Multiseat M2b (MS2, MS5): Installer mit und ohne Marker multiseat.aktiv, ausgeführt mit Ersatzprogrammen.

MS2: ohne Marker erzeugt der Installer exakt dieselben Aufrufe und Dateien wie 0.17.6 (eingefrorene Kopie).
MS5: mit Marker wird /etc/sddm.conf nicht geschrieben, sddm nicht neu gestartet, der Kiosk trotzdem eingerichtet.
"""
from __future__ import annotations

import pytest
from _installer_env import _ETC, OLD, Installer

SDDM_RESTART = "systemctl restart sddm"
ORIG_SDDM = "[Theme]\nCurrent=breeze\n"


def _pair(tmp_path, **kw):
    old, new = Installer(tmp_path / "alt", OLD, **kw), Installer(tmp_path / "neu", **kw)
    return old, new


@pytest.mark.parametrize("kw, openbox", [({}, False), ({}, True), ({"monitor": True}, False), ({"sddm": False}, False)],
                         ids=["kiosk", "kiosk-openbox-alt", "monitor-kein-kiosk", "ohne-sddm"])
def test_ms2_ohne_marker_wie_0176(tmp_path, kw, openbox):
    old, new = _pair(tmp_path, **kw)
    r_old, r_new = old.run(openbox=openbox), new.run(openbox=openbox)
    assert r_old.returncode == 0 and r_new.returncode == 0, r_new.stderr
    assert new.calls() == old.calls()
    assert new.files() == old.files()
    assert new.out(r_new) == old.out(r_old)


def test_ms2_vergleich_greift(tmp_path):
    """Der Vergleich selbst ist scharf: der Kiosk-Lauf startet sddm neu und schreibt die Kiosk-sddm.conf."""
    old, new = _pair(tmp_path)
    old.run(), new.run()
    assert SDDM_RESTART in new.calls()
    assert "User=hydrahive-kiosk" in new.etc("sddm.conf").read_text()
    assert "Kiosk-Einrichtung fehlgeschlagen" not in new.out(new.run())


def test_ms5_marker_sddm_unberuehrt_kiosk_eingerichtet(tmp_path):
    inst = Installer(tmp_path, multiseat=True, monitor=True, sddm=False)   # Monitor gehört seat1, sddm ist aus
    r = inst.run(openbox=True)
    assert r.returncode == 0, r.stderr
    assert inst.etc("sddm.conf").read_text() == ORIG_SDDM                    # nicht geschrieben
    assert not (inst.root / _ETC.lstrip("/") / "sddm.conf.vor-vitrine").exists()
    c = inst.calls()
    assert not any("sddm" in x and ("restart" in x or "cat " in x) for x in c), c
    assert any("kiosk-install.sh" in x for x in c)                             # Kiosk trotz Monitor eingerichtet
    assert (inst.root / "usr/share/xsessions/hydrahive-vitrine-kiosk.desktop").is_file()
    assert "VITRINE_KIOSK_DISPLAY=:0" in inst.etc("systemd/system/hydrahive2-vitrine.service").read_text()
    assert (inst.root / _ETC.lstrip("/") / "multiseat.aktiv").is_file()     # Zustand bleibt
    assert "Monitor" not in r.stdout and "lightdm bleibt unverändert" in r.stdout


def test_ms5_update_zweimal_mit_marker(tmp_path):
    """Update = install.sh erneut: auch der zweite Lauf lässt sddm und die lightdm-Seite in Ruhe."""
    inst = Installer(tmp_path, multiseat=True, sddm=False)
    lightdm = inst.etc("lightdm/lightdm.conf.d/50-hydrahive-multiseat.conf")
    lightdm.parent.mkdir(parents=True)
    lightdm.write_text("[Seat:seat0]\nautologin-user=hydrahive-kiosk\n")
    assert inst.run().returncode == 0 and inst.run().returncode == 0
    assert inst.etc("sddm.conf").read_text() == ORIG_SDDM
    assert lightdm.read_text() == "[Seat:seat0]\nautologin-user=hydrahive-kiosk\n"
    assert SDDM_RESTART not in inst.calls()


def test_kiosk_uninstall_schaltet_zuerst_aus(tmp_path):
    inst = Installer(tmp_path, multiseat=True)
    etc = inst.root / _ETC.lstrip("/")
    (etc / "multiseat-revert.sh").write_text('#!/bin/bash\necho "REVERT $HH_MULTISEAT_CHECK_SECONDS" >> "$HH_FAKE_LOG"\n')
    (etc / "sddm.conf.vor-vitrine").write_text(ORIG_SDDM)
    r = inst.run("kiosk-uninstall.sh")
    assert r.returncode == 0, r.stderr
    c = inst.calls()
    assert c[0] == "REVERT 1", c                                               # zuerst ausschalten
    assert c.index("REVERT 1") < next(i for i, x in enumerate(c) if x.startswith("userdel"))
    assert not etc.exists()


def test_kiosk_uninstall_ohne_marker_wie_0176(tmp_path):
    old, new = _pair(tmp_path)
    for i in (old, new):
        (i.root / _ETC.lstrip("/")).mkdir(parents=True)
        (i.root / _ETC.lstrip("/") / "sddm.conf.vor-vitrine").write_text(ORIG_SDDM)
        (i.root / _ETC.lstrip("/") / "multiseat-revert.sh").write_text('#!/bin/bash\necho REVERT >> "$HH_FAKE_LOG"\n')
    assert old.run("kiosk-uninstall.sh").returncode == 0 and new.run("kiosk-uninstall.sh").returncode == 0
    assert new.calls() == old.calls() and "REVERT" not in new.calls()
    assert new.files() == old.files()
