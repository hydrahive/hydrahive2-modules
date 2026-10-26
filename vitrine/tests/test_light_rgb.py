"""S8: OpenRGB-Aufruf – feste Argumentliste, nur geprüfte Werte, Fehler auch bei rc 0 erkennen (am 26.10. gemessen)."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from renderer import light_rgb as rgb
from renderer.light_state import Look

LIST_OUT = """[i2c_smbus_linux] Failed to read i2c device PCI device ID
0: Irgendeine Tastatur
  Type:           Keyboard
1: B850 AORUS ELITE X3D
  Type:           Motherboard
  Description:    IT5711-GIGABYTE V1.0.09.C
  Location:       HID: /dev/hidraw1
"""


@pytest.fixture
def fake(tmp_path: Path):
    """openrgb-Attrappe: schreibt Argumente + Umgebung auf; Ausgabe/rc über Steuerdateien."""
    b = tmp_path / "bin"
    b.mkdir()
    log = tmp_path / "calls.log"
    (b / "openrgb").write_text(f'''#!/bin/bash
echo "$*" >> "{log}"
echo "HOME=$HOME" >> "{log}"
if [ "$1" = "--noautoconnect" ] && [[ " $* " == *" -l "* ]]; then cat "{tmp_path}/list.txt" 2>/dev/null; exit 0; fi
cat "{tmp_path}/out.txt" 2>/dev/null
exit $(cat "{tmp_path}/rc.txt" 2>/dev/null || echo 0)
''')
    (b / "openrgb").chmod(0o755)
    (tmp_path / "list.txt").write_text(LIST_OUT)
    return {"bin": str(b / "openrgb"), "log": log, "tmp": tmp_path, "cfg": tmp_path / "orgb"}


def _calls(f) -> list[str]:
    return [ln for ln in f["log"].read_text().splitlines() if not ln.startswith("HOME=")]


def test_find_nimmt_das_mainboard(fake) -> None:
    dev = rgb.find(fake["cfg"], binary=fake["bin"])
    assert dev == rgb.Device(index=1, name="B850 AORUS ELITE X3D")
    assert _calls(fake)[0] == f"--noautoconnect --config {fake['cfg']} -l"


def test_find_ohne_mainboard(fake) -> None:
    (fake["tmp"] / "list.txt").write_text("0: Maus\n  Type:           Mouse\n")
    assert rgb.find(fake["cfg"], binary=fake["bin"]) is None


def test_find_ohne_programm(tmp_path) -> None:
    assert rgb.find(tmp_path / "c", binary=str(tmp_path / "gibtsnicht")) is None


@pytest.mark.parametrize("look, tail", [
    (Look("working", "breathing", "0060FF", 80, 30), "-m breathing -c 0060FF -b 80 -s 30"),
    (Look("error", "flashing", "FF0000", 100, 70), "-m flashing -c FF0000 -b 100 -s 70"),
    (Look("autumn", "static", "FF8C1A", 50, 50), "-m static -c FF8C1A -b 50"),
    (Look("night", "off", "000000", 0), "-m static -c 000000 -b 0"),
    (Look("working", "off", "0060FF", 80, 30), "-m static -c 000000 -b 0"),
])
def test_befehlszeile(fake, look, tail) -> None:
    args = rgb.command(look, rgb.Device(1, "X"), fake["cfg"], binary="openrgb")
    assert args == ["openrgb", "--noautoconnect", "--config", str(fake["cfg"]), "-d", "1", *tail.split()]


@pytest.mark.parametrize("bad", [
    Look("x", "rainbow", "FF0000", 50), Look("x", "static", "FF00", 50), Look("x", "static", "FF0000; rm", 50),
    Look("x", "static", "FF0000", 101), Look("x", "static", "FF0000", -1), Look("x", "breathing", "FF0000", 50, 200),
])
def test_ungepruefte_werte_werden_abgelehnt(fake, bad) -> None:
    with pytest.raises(rgb.LightError):
        rgb.command(bad, rgb.Device(1, "X"), fake["cfg"], binary="openrgb")


def test_apply_setzt_und_nutzt_eigenen_ordner(fake) -> None:
    rgb.apply(Look("working", "breathing", "0060FF", 80, 30), rgb.Device(1, "X"), fake["cfg"], binary=fake["bin"])
    assert _calls(fake)[-1].endswith("-d 1 -m breathing -c 0060FF -b 80 -s 30")
    assert f"HOME={fake['cfg']}" in fake["log"].read_text()           # nichts unter dem echten $HOME (ProtectHome)
    assert fake["cfg"].is_dir()


def test_apply_erkennt_fehler_auch_bei_rc_0(fake) -> None:
    (fake["tmp"] / "out.txt").write_text("Error: Mode 'breathing' not available for device 'X'\n")
    with pytest.raises(rgb.LightError, match="not available"):
        rgb.apply(Look("working", "breathing", "0060FF", 80, 30), rgb.Device(1, "X"), fake["cfg"], binary=fake["bin"])


def test_apply_erkennt_rc(fake) -> None:
    (fake["tmp"] / "rc.txt").write_text("255")
    (fake["tmp"] / "out.txt").write_text("Error: Empty device ID\n")
    with pytest.raises(rgb.LightError):
        rgb.apply(Look("autumn", "static", "FF8C1A", 50), rgb.Device(1, "X"), fake["cfg"], binary=fake["bin"])


def test_apply_zeitlimit(fake) -> None:
    def hangs(*a, **k):
        raise subprocess.TimeoutExpired(cmd="openrgb", timeout=1)
    with pytest.raises(rgb.LightError, match="Zeit"):
        rgb.apply(Look("autumn", "static", "FF8C1A", 50), rgb.Device(1, "X"), fake["cfg"], binary=fake["bin"],
                  run=hangs)


def test_nie_shell(fake, monkeypatch) -> None:
    seen = {}

    def spy(args, **kw):
        seen.update(kw, args=args)
        return subprocess.CompletedProcess(args, 0, "", "")
    rgb.apply(Look("autumn", "static", "FF8C1A", 50), rgb.Device(1, "X"), fake["cfg"], binary=fake["bin"], run=spy)
    assert isinstance(seen["args"], list) and not seen.get("shell") and seen.get("timeout")
    assert os.environ.get("HOME") != str(fake["cfg"])
