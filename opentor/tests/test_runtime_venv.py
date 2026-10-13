"""OpenTor-venv folgt dem HydraHive-Python (Kern-Spec python-314-umstieg).

Prod: opentor-runtime/venv ist mit 3.12 gebaut. install.sh legte das venv nur
an, wenn bin/python fehlte — nach dem Umstieg des Kerns auf 3.14 und dem
Entfernen von 3.12 zeigte bin/python ins Leere, ohne dass ein Neubau anlief.

Geprüft wird nur der venv-Teil von install.sh (bis vor die Tor-Provisionierung),
ohne Netz: git, pip-Install und Tor liegen außerhalb des Abschnitts.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

INSTALL = Path(__file__).resolve().parents[1] / "extension" / "install.sh"
MINOR = "%d.%d" % sys.version_info[:2]


def _venv_section() -> str:
    text = INSTALL.read_text()
    start = text.index("# --- Python-venv ---")
    end = text.index("# --- Ende Python-venv ---")
    return text[start:end]


def _run(runtime: Path, python: str) -> subprocess.CompletedProcess[str]:
    script = (
        'set -euo pipefail\nVENV="$1"\n'
        f"{_venv_section()}\n"
    )
    return subprocess.run(
        ["bash", "-c", script, "venv", str(runtime / "venv")],
        capture_output=True, text=True,
        env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": os.environ.get("HOME", "/tmp"),
             "HYDRAHIVE_OPENTOR_BASE_PYTHON": python, "LANG": "C.UTF-8"},
    )


def _minor(venv: Path) -> str:
    return subprocess.check_output(
        [str(venv / "bin" / "python"), "-c", "import sys; print('%d.%d' % sys.version_info[:2])"], text=True,
    ).strip()


def test_dangling_interpreter_triggers_rebuild(tmp_path: Path) -> None:
    venv = tmp_path / "venv"
    (venv / "bin").mkdir(parents=True)
    (venv / "bin" / "python").symlink_to("/usr/bin/python3.12-entfernt")

    result = _run(tmp_path, sys.executable)

    assert result.returncode == 0, result.stderr
    assert _minor(venv) == MINOR
    assert "neu" in result.stdout


def test_matching_venv_is_kept(tmp_path: Path) -> None:
    venv = tmp_path / "venv"
    subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
    marker = venv / "keep-me"
    marker.write_text("x")

    result = _run(tmp_path, sys.executable)

    assert result.returncode == 0, result.stderr
    assert marker.exists()


def test_base_python_defaults_to_core_interpreter() -> None:
    """Ohne Vorgabe: das Python, mit dem HydraHive läuft (Kern-venv)."""
    section = _venv_section()

    assert "HYDRAHIVE_OPENTOR_BASE_PYTHON" in section
    assert "/opt/hydrahive2/.venv/bin/python" not in section  # kein fester Pfad
    assert "-m venv --clear" in section


def test_core_passes_its_interpreter_to_install_script() -> None:
    """install.sh läuft aus dem Kern (modules/installer.py) — dort zeigt python3
    im PATH auf das Kern-venv (Unit: PATH=/opt/hydrahive2/.venv/bin:...)."""
    section = _venv_section()

    assert "command -v python3" in section
    assert "readlink -f" in section
