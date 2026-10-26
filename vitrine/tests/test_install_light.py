"""S8: Installer-Teil fürs Mainboard-Licht (extension/light-install.sh). Nachgebaute Befehle (lsusb, apt-get, sudo …)."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

EXT = Path(__file__).resolve().parents[1] / "extension"
LSUSB_IT5711 = "Bus 001 Device 003: ID 048d:5711 Integrated Technology Express, Inc. GIGABYTE Device\n"


def _exe(p: Path, body: str) -> None:
    p.write_text("#!/bin/bash\n" + body)
    p.chmod(0o755)


@pytest.fixture
def box(tmp_path: Path) -> dict:
    b = tmp_path / "bin"
    b.mkdir()
    calls = tmp_path / "calls.log"
    calls.write_text("")
    log = f'echo "$(basename "$0") $*" >> "{calls}"\n'
    _exe(b / "lsusb", f'cat "{tmp_path}/lsusb.txt" 2>/dev/null\n')
    _exe(b / "sudo", log + '[ "$1" = "-n" ] && shift\nexec "$@"\n')
    _exe(b / "apt-get", log + f'touch "{tmp_path}/installed"\n')
    _exe(b / "udevadm", log)
    _exe(b / "tee", log + f'cat > "{tmp_path}/rule.txt"\n')
    _exe(b / "rm", log)
    _exe(b / "openrgb", "exit 0\n")
    (tmp_path / "data").mkdir()
    return {"tmp": tmp_path, "bin": b, "calls": calls}


def _run(box: dict, script: str = "light-install.sh", *, with_openrgb: bool = False, **env) -> subprocess.CompletedProcess:
    path = f"{box['bin']}:/usr/bin:/bin"
    if not with_openrgb:
        (box["bin"] / "openrgb").unlink(missing_ok=True)
    e = {**os.environ, "PATH": path, "VITRINE_LIGHT_RULE": str(box["tmp"] / "72.rules"), "USER_NAME": "hydrahive",
         "DATA": str(box["tmp"] / "data"), **env}
    return subprocess.run(["bash", str(EXT / script)], env=e, capture_output=True, text=True, timeout=30)


def _calls(box: dict) -> list[str]:
    return box["calls"].read_text().splitlines()


def test_ohne_lichtchip_nichts(box) -> None:
    r = _run(box)
    assert r.returncode == 0, r.stderr
    assert _calls(box) == [] and "kein unterstützter" in r.stdout


def test_mit_lichtchip_openrgb_und_regel(box) -> None:
    (box["tmp"] / "lsusb.txt").write_text(LSUSB_IT5711)
    r = _run(box)
    assert r.returncode == 0, r.stderr
    c = _calls(box)
    assert any(x.startswith("apt-get") and "--no-install-recommends" in x and x.endswith("openrgb") for x in c), c
    rule = (box["tmp"] / "rule.txt").read_text()
    assert 'SUBSYSTEM=="hidraw"' in rule and 'ATTRS{idVendor}=="048d"' in rule and 'ATTRS{idProduct}=="5711"' in rule
    assert 'GROUP="hydrahive"' in rule and 'MODE="0660"' in rule
    assert any(x.startswith("udevadm trigger") and "hidraw" in x for x in c), c


def test_openrgb_schon_da_kein_apt(box) -> None:
    (box["tmp"] / "lsusb.txt").write_text(LSUSB_IT5711)
    _run(box, with_openrgb=True)
    assert not any(x.startswith("apt-get") for x in _calls(box))
    assert (box["tmp"] / "rule.txt").exists()


def test_abschaltbar(box) -> None:
    (box["tmp"] / "lsusb.txt").write_text(LSUSB_IT5711)
    (box["tmp"] / "data" / "light.off").write_text("")
    r = _run(box)
    assert _calls(box) == [] and "abgeschaltet" in r.stdout


def test_fehler_beim_installieren_bricht_nicht_ab(box) -> None:
    (box["tmp"] / "lsusb.txt").write_text(LSUSB_IT5711)
    _exe(box["bin"] / "apt-get", "exit 100\n")
    r = _run(box)
    assert r.returncode == 0 and "OpenRGB nicht installiert" in r.stdout + r.stderr


def test_rueckbau_entfernt_nur_die_regel(box) -> None:
    r = _run(box, "light-uninstall.sh")
    assert r.returncode == 0, r.stderr
    c = _calls(box)
    assert any(x == f"rm -f {box['tmp'] / '72.rules'}" for x in c), c
    assert not any(x.startswith("apt-get") for x in c), "OpenRGB bleibt (normales Systempaket)"


def test_install_sh_ruft_licht_teil_auf_und_uninstall_den_rueckbau() -> None:
    inst, uninst = (EXT / "install.sh").read_text(), (EXT / "uninstall.sh").read_text()
    assert "light-install.sh" in inst and "light-uninstall.sh" in uninst
    line = next(ln for ln in inst.splitlines() if "light-install.sh" in ln)
    assert "||" in line, "Licht darf die Installation nie abbrechen"


@pytest.mark.parametrize("script", ["light-install.sh", "light-uninstall.sh"])
def test_sudo_nur_mit_bash(script) -> None:
    """sudoers des Installers erlaubt nur `sudo -n bash` (Kommentar in install.sh) – sudo tee/udevadm/rm scheitern dort."""
    lines = [ln for ln in (EXT / script).read_text().splitlines() if not ln.lstrip().startswith("#")]
    for ln in lines:
        for part in ln.split("sudo ")[1:]:
            assert part.startswith("-n bash "), f"nur sudo -n bash erlaubt: {ln.strip()}"


def test_shell_syntax() -> None:
    for f in ("light-install.sh", "light-uninstall.sh"):
        subprocess.run(["bash", "-n", str(EXT / f)], check=True)
