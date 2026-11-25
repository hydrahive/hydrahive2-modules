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


@pytest.mark.parametrize("kw, openbox", [({}, False), ({}, True), ({"sddm": False}, False)],
                         ids=["kiosk", "kiosk-openbox-alt", "ohne-sddm"])
def test_ms2_ohne_marker_wie_0176(tmp_path, kw, openbox):
    """Ohne Monitor und ohne Marker wie 0.17.6. Den Fall „Monitor angeschlossen“ ändert §7 N1 bewusst
    (test_multiseat_immer.py::test_n1_monitor_kiosk_wie_ohne_monitor)."""
    old, new = _pair(tmp_path, **kw)
    r_old, r_new = old.run(openbox=openbox), new.run(openbox=openbox)
    assert r_old.returncode == 0 and r_new.returncode == 0, r_new.stderr
    assert new.calls() == old.calls()
    # Gewollte Abweichungen (alles andere muss identisch zu 0.17.6 sein):
    # - Inhalt zweier nach /etc kopierter Skripte: kiosk-uninstall.sh schaltet seit M2b zuerst den zweiten Arbeitsplatz
    #   aus (eigener Test unten); kiosk-session.sh lässt seit §7 N2b einen fremden Monitor an (test_multiseat_immer.py).
    # - MS12 (0.18.2): die Website-Sperre steht nicht mehr systemweit in /etc/firefox/policies/policies.json, sondern
    #   nur im user.js des Kiosk-Profils (test_firefox_sperre.py). Die alte Datei fehlt also, user.js ist länger.
    f_new, f_old = new.files(), old.files()
    for script in ("etc/hydrahive2-vitrine/kiosk-uninstall.sh", "etc/hydrahive2-vitrine/kiosk-session.sh"):
        assert (script in f_new) == (script in f_old)
        f_new.pop(script, None), f_old.pop(script, None)
    policy, userjs = "etc/firefox/policies/policies.json", "home/hydrahive-kiosk/firefox/user.js"
    assert policy not in f_new and (policy in f_old) == (userjs in f_old) == (userjs in f_new)   # nur mit Kiosk
    if userjs in f_old:
        f_old.pop(policy)
        assert f_new[userjs].startswith(f_old[userjs]) and 'user_pref("network.proxy.type", 1);' in f_new[userjs]
        f_new.pop(userjs), f_old.pop(userjs)
    assert f_new == f_old
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
