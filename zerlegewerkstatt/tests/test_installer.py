"""Installer: gepinnte Versionen, Grenzen und Nachvollziehbarkeit."""
from __future__ import annotations

import re
from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parents[1]
INSTALL = MODULE_DIR / "extension" / "install.sh"
UNINSTALL = MODULE_DIR / "extension" / "uninstall.sh"


def read(path: Path) -> str:
    return path.read_text()


def test_install_und_uninstall_existieren():
    assert INSTALL.is_file()
    assert UNINSTALL.is_file()


def test_versionen_sind_gepinnt():
    text = read(INSTALL)
    assert 'NODE_VERSION="24.22.2"' in text
    assert 'REA_VERSION="6.8.0"' in text
    assert 'GHIDRA_VERSION="12.1.4"' in text
    assert 'JADX_VERSION="0.7.1"' in text


def test_jede_quelle_hat_eine_pruefsumme():
    text = read(INSTALL)
    downloads = re.findall(r'^(NODE|REA|GHIDRA|JADX)_URL="([^"]+)"', text, re.MULTILINE)
    checksums = dict(re.findall(r'^(NODE|REA|GHIDRA|JADX)_SHA256="([0-9a-f]{64})"',
                                text, re.MULTILINE))
    assert len(downloads) == 4
    for name, _url in downloads:
        assert name in checksums, f"{name} hat keine Pruefsumme"


def test_keine_ungestuetzte_quelle_wird_geladen():
    """Kein 'latest', jeder Download laeuft ueber fetch_verified."""
    text = read(INSTALL)
    assert "/latest" not in text
    assert "fetch_verified" in text
    for name in ("NODE_URL", "REA_URL", "GHIDRA_URL", "JADX_URL"):
        assert re.search(rf'fetch_verified "\${name}"', text), f"{name} wird nicht geprueft"


def test_container_bleibt_unprivilegiert():
    text = read(INSTALL)
    assert "security.privileged false" in text
    assert "security.nesting false" in text
    assert "unconfined" not in text
    assert "privileged=true" not in text


def test_ressourcenlimits_werden_gesetzt():
    text = read(INSTALL)
    assert "limits.cpu" in text
    assert "limits.memory" in text
    assert 'CPU_LIMIT="${CPU_LIMIT:-6}"' in text
    assert 'MEMORY_LIMIT="${MEMORY_LIMIT:-12GiB}"' in text


def test_apparmor_bleibt_minimal():
    """Nur signal und ptrace, wie SPEC §7 es erlaubt."""
    text = read(INSTALL)
    match = re.search(r'raw\.apparmor "([^"]*)"', text, re.DOTALL)
    assert match, "AppArmor-Regeln fehlen"
    rules = [rule.strip() for rule in match.group(1).split(",") if rule.strip()]
    assert rules == ["signal", "ptrace"]


def test_keine_host_freigaben():
    """Kein Socket, kein /dev, kein Host-Workspace."""
    text = read(INSTALL)
    for verboten in ("/var/lib/docker.sock", "security.sock", "host_device",
                     "security.devl", "/var/lib/hydrahive2/workspaces"):
        assert verboten not in text, f"{verboten} darf nicht vorkommen"


def test_pruefsummenabweichung_bricht_ab():
    text = read(INSTALL)
    assert "Pruefsumme weicht ab" in text
    assert "rm -f \"$target.part\"" in text


def test_uninstall_behaelt_die_falldaten():
    text = read(UNINSTALL)
    assert "Falldaten bleiben erhalten" in text
    assert "incus delete" in text


def test_installation_verlangt_incus_aber_kein_root():
    """Der Kern ruft das Script als normalen Benutzer auf
    (core/src/hydrahive/modules/installer.py: subprocess.run(["bash", path])).
    Eine root-Pflicht bricht die Installation im Hub ab."""
    text = read(INSTALL)
    assert "require_incus" in text
    assert "command -v incus" in text
    assert "require_root" not in text
    assert "id -u" not in text
    assert "Das Skript braucht root" not in text
    # Incus wird ueber die incus-admin-Gruppe verwaltet, nicht ueber root.
    assert "incus-admin" in text or "incus query" in text


def test_dateien_werden_einzeln_in_den_container_gepusht():
    """`incus file push -r` legt bei einem Verzeichnis einen zusaetzlichen
    Ordner mit dem Verzeichnisnamen an - dann landen die Werkzeuge eine
    Ebene zu tief und die Installation scheitert."""
    text = read(INSTALL)
    assert "for file in" in text
    # Nur die Verwendung als Argument zaehlt, nicht der Kommentar dazu.
    aufrufe = [line for line in text.splitlines()
               if "incus file push" in line and not line.strip().startswith("#")]
    assert aufrufe, "es wird nichts in den Container kopiert"
    assert not any(" -r" in line for line in aufrufe)


def test_analyse_laeuft_offline():
    """Der Adapter schaltet das Netz vor der Analyse ab."""
    from backend import runtime

    text = read(MODULE_DIR / "backend" / "runtime.py")
    assert "disable_network" in text
    assert "enable_network" in text
    assert runtime.CONTAINER_NAME == "hh-zerlegewerkstatt"
