"""Kiosk-Sitzung: Openbox ohne Menüs und Tastenkürzel (Befund 19.10.2026 auf .2).

Die Sitzung startete Openbox mit der Standard-Konfiguration (/etc/xdg/openbox/rc.xml): Rechtsklick auf den Hintergrund
öffnet ein Menü mit „Terminal emulator“ und „Exit“, Alt+Leertaste ein Fenstermenü. Mit einer Bluetooth-Tastatur wäre das
eine Shell als Kiosk-Nutzer an der Statuszentrale vorbei. Deshalb: eigene, leere Konfiguration.
"""
from __future__ import annotations

import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

EXT = Path(__file__).resolve().parents[1] / "extension"
RC = EXT / "kiosk-openbox.xml"
NS = {"ob": "http://openbox.org/3.4/rc"}


def _tree():
    return ET.parse(RC).getroot()


def test_konfiguration_ist_gueltiges_openbox_xml():
    root = _tree()
    assert root.tag == "{http://openbox.org/3.4/rc}openbox_config"


def test_keine_tastenkuerzel_keine_maus_aktionen_kein_menue():
    root = _tree()
    assert root.findall(".//ob:keybind", NS) == [], "keine Tastenkürzel"
    assert root.findall(".//ob:mousebind", NS) == [], "keine Mausaktionen (Rechtsklick-Menü)"
    menus = root.findall(".//ob:menu/ob:file", NS)
    assert menus == [], "kein Menü-File (Standard enthält „Terminal emulator“)"
    import re
    text = re.sub(r"<!--.*?-->", "", RC.read_text(), flags=re.S).lower()       # nur Einstellungen, keine Kommentare
    for verboten in ("execute", "terminal", "showmenu", "exit", "restart", "reconfigure", "x-terminal-emulator"):
        assert verboten not in text, verboten


def test_kiosk_fenster_ohne_rahmen_und_vollbild():
    root = _tree()
    apps = root.findall(".//ob:applications/ob:application", NS)
    assert apps and apps[0].get("class") == "*"
    assert apps[0].find("ob:decor", NS).text == "no"
    assert apps[0].find("ob:fullscreen", NS).text == "yes"


def test_sitzung_startet_openbox_nur_mit_eigener_konfiguration():
    s = (EXT / "kiosk-session.sh").read_text()
    lines = [ln.strip() for ln in s.splitlines() if "openbox" in ln and not ln.strip().startswith("#")]
    assert lines, "openbox wird gestartet"
    assert all("--config-file" in ln and "/etc/hydrahive2-vitrine/openbox.xml" in ln for ln in lines if ln.startswith("openbox")), lines


def test_installer_legt_konfiguration_ab_rueckbau_entfernt_sie():
    inst = (EXT / "kiosk-install.sh").read_text()
    assert 'install -m 644 "${MODULE_ROOT}/extension/kiosk-openbox.xml" "${CONF}/openbox.xml"' in inst
    assert inst.index("kiosk-openbox.xml") < inst.index('pkill -u "${KIOSK}"'), "erst Konfiguration, dann Neustart"
    rueck = (EXT / "kiosk-uninstall.sh").read_text()
    assert "/etc/hydrahive2-vitrine" in rueck


def test_installer_startet_sitzung_neu_damit_openbox_die_konfiguration_laedt():
    """Openbox liest die Datei nur beim Start. Gemessen 19.10.2026 17:24 auf .2: `loginctl terminate-user` beendet auch
    den sddm-helper → sddm meldet „Process crashed“ und meldet NICHT neu an (Relogin greift nicht), Display bleibt
    schwarz. `systemctl restart sddm` brachte die Sitzung binnen 2 s zurück (wie schon im Rückbau)."""
    inst = (EXT / "kiosk-install.sh").read_text()
    code = "\n".join(ln for ln in inst.splitlines() if not ln.strip().startswith("#"))
    assert "terminate-user" not in code, "beendet den sddm-helper – sddm meldet dann nicht neu an"
    assert 'pgrep -u "${KIOSK}" -x openbox' in code and "systemctl restart sddm" in code
    i, j = code.index('pgrep -u "${KIOSK}" -x openbox'), code.index("systemctl restart sddm")
    assert i < j and '! pgrep -u "${KIOSK}" -f -- "--config-file /etc/hydrahive2-vitrine/openbox.xml"' in code[i:j], \
        "nur neu starten, wenn ein Openbox OHNE die eigene Datei läuft"


def _run_install_tail(tmp_path, procs: list[str]) -> list[str]:
    """Nur den Neustart-Teil des Installers mit gefälschtem pgrep/systemctl ausführen; liefert die systemctl-Aufrufe."""
    import re
    inst = (EXT / "kiosk-install.sh").read_text()
    block = re.search(r'(if pgrep -u "\$\{KIOSK\}" -x openbox.*?\nfi)', inst, re.S).group(1)
    bindir = tmp_path / "bin"
    bindir.mkdir(parents=True)
    (tmp_path / "procs").write_text("\n".join(procs) + "\n")
    (bindir / "pgrep").write_text("""#!/bin/bash
# -x NAME: genauer Programmname; -f MUSTER: ganze Kommandozeile (Muster nach --)
if [ "$3" = "-x" ]; then grep -q "^$4\\b" "$PROCS"; else pat="${@: -1}"; grep -qF -- "$pat" "$PROCS"; fi
""")
    (bindir / "systemctl").write_text('#!/bin/bash\necho "systemctl $*" >> "$CALLS"\n')
    for f in bindir.iterdir():
        f.chmod(0o755)
    calls = tmp_path / "calls"
    calls.write_text("")
    env = {"PATH": f"{bindir}:/usr/bin:/bin", "PROCS": str(tmp_path / "procs"), "CALLS": str(calls)}
    subprocess.run(["bash", "-c", 'KIOSK=hydrahive-kiosk\n' + block], env=env, check=True)
    return [ln for ln in calls.read_text().splitlines() if ln]


def test_neustart_nur_beim_wechsel_von_standard_openbox(tmp_path):
    assert _run_install_tail(tmp_path / "a", ["openbox"]) == ["systemctl restart sddm"], "altes Openbox → einmal neu"


def test_kein_neustart_wenn_openbox_schon_mit_eigener_konfiguration_laeuft(tmp_path):
    procs = ["openbox --config-file /etc/hydrahive2-vitrine/openbox.xml"]
    assert _run_install_tail(tmp_path / "b", procs) == [], "jedes weitere Update: kein Schwarzbild"


def test_kein_neustart_ohne_laufende_sitzung(tmp_path):
    assert _run_install_tail(tmp_path / "c", ["firefox"]) == []


@pytest.mark.skipif(not shutil.which("openbox"), reason="openbox fehlt")
def test_openbox_akzeptiert_die_datei():
    out = subprocess.run(["xmllint", "--noout", str(RC)], capture_output=True, text=True, check=False) \
        if shutil.which("xmllint") else None
    assert out is None or out.returncode == 0, out.stderr
