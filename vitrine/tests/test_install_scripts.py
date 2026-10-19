"""Installer-Skripte: Der Kiosk-Teil muss außerhalb der HydraHive-Sandbox laufen.

Anlass (Update 19.10.2026 auf .2): install.sh läuft aus dem HydraHive-Dienst mit ProtectHome=read-only; auch `sudo -n bash`
erbt diesen Mount-Namespace → `useradd -m` scheiterte an /home (Exit 12), danach `install -d /home/…` (Read-only file system).
Belegt am Gerät: dieselbe Kette mit `systemd-run` als Zwischenschritt kann /home schreiben.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

EXT = Path(__file__).resolve().parents[1] / "extension"


def _lines(name: str) -> list[str]:
    return [ln for ln in (EXT / name).read_text().splitlines() if not ln.lstrip().startswith("#")]


def test_kiosk_install_laeuft_ueber_systemd_run():
    calls = [ln for ln in _lines("install.sh") if "kiosk-install.sh" in ln and "sudo -n" in ln]
    assert calls, "install.sh ruft kiosk-install.sh auf"
    assert all("systemd-run" in ln for ln in calls), "ohne systemd-run bleibt /home schreibgeschützt (ProtectHome)"


def test_kiosk_rueckbau_laeuft_ueber_systemd_run():
    text = "\n".join(_lines("uninstall.sh"))
    assert re.search(r"systemd-run[^\n]*\n?[^\n]*kiosk-uninstall\.sh", text), "verzögerter Rückbau per systemd-run"


def test_systemd_run_wartet_und_meldet_fehler():
    """--wait + --pipe: install.sh soll auf das Ergebnis warten und den Exit-Code des Kiosk-Teils sehen."""
    call = next(ln for ln in _lines("install.sh") if "kiosk-install.sh" in ln and "systemd-run" in ln)
    assert "--wait" in call and "--pipe" in call


def test_kiosk_fehler_bricht_den_dienst_nicht():
    """Scheitert der Kiosk, muss der Vitrine-Dienst trotzdem eingerichtet werden (Video läuft weiter) – am 19.10. fiel der
    Dienst mit dem Kiosk aus und das Display blieb dunkel."""
    call = next(ln for ln in _lines("install.sh") if "kiosk-install.sh" in ln and "sudo -n" in ln)
    assert call.rstrip().endswith("then"), "Kiosk-Aufruf als if-Bedingung (set -e bricht dann nicht ab)"
    text = "\n".join(_lines("install.sh"))
    assert "Kiosk-Einrichtung fehlgeschlagen" in text and "KIOSK_ENV=\"\"" in text


def test_shell_syntax():
    for f in sorted(EXT.glob("*.sh")):
        subprocess.run(["bash", "-n", str(f)], check=True)
