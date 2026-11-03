"""Installer: gepinnte Versionen, Grenzen und Nachvollziehbarkeit."""
from __future__ import annotations

import os
import re
import subprocess
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
    assert '"version": "0.3.0"' in read(MODULE_DIR / "manifest.json")
    assert 'NODE_VERSION="24.22.2"' in text
    assert 'REA_VERSION="6.8.0"' in text
    assert 'GHIDRA_VERSION="12.1.4"' in text
    assert 'JADX_VERSION="0.7.1"' in text
    assert 'BINWALK_VERSION="3.1.0"' in text
    assert 'RUST_VERSION="1.81.0"' in text
    assert 'SASQUATCH_RELEASE="sasquatch-v4.5.1-4"' in text


def test_jede_quelle_hat_eine_pruefsumme():
    text = read(INSTALL)
    downloads = re.findall(r'^(REA|GHIDRA|JADX|BINWALK)_URL="([^"]+)"', text, re.MULTILINE)
    checksums = dict(re.findall(r'^(REA|GHIDRA|JADX|BINWALK)_SHA256="([0-9a-f]{64})"',
                                text, re.MULTILINE))
    assert len(downloads) == 4
    for name, _url in downloads:
        assert name in checksums, f"{name} hat keine Pruefsumme"
    # Node ist architekturabhängig; beide offiziellen SHAs stehen im case-Block.
    assert "nodejs.org/dist" in text
    assert len(re.findall(r'NODE_SHA256="[0-9a-f]{64}"', text)) == 2


def test_keine_ungestuetzte_quelle_wird_geladen():
    """Kein 'latest', jeder Download laeuft ueber fetch_verified."""
    text = read(INSTALL)
    assert "/latest" not in text
    assert "fetch_verified" in text
    for name in ("NODE_URL", "RUST_URL", "REA_URL", "GHIDRA_URL", "JADX_URL", "BINWALK_URL", "SASQUATCH_URL"):
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


def test_binwalk_31_wird_gepinnt_gebaut_und_geprueft():
    text = read(INSTALL)
    assert 'BINWALK_VERSION="3.1.0"' in text
    assert "99d5dc70f5021c55624f098adae4d1de9c1c07d000475664704b675aad7e0811" in text
    assert "RUSTC=/opt/rust/bin/rustc /opt/rust/bin/cargo install" in text
    assert "--locked" in text
    assert "--root /opt/binwalk" in text
    assert "/opt/rust/bin/rustc --version" in text
    assert "/opt/binwalk/bin/binwalk --version" in text
    assert 'rm -rf /opt/rust' in text
    assert 'rm -rf /opt/binwalk' in text
    assert 'dpkg -i "$staging/$7"' in text
    assert "command -v sasquatch" in text
    from backend import runtime
    assert runtime.BINWALK_COMMAND == "/opt/binwalk/bin/binwalk"
    assert "REA_BINWALK_COMMAND" in read(MODULE_DIR / "backend" / "runtime.py")


def test_pcap_hat_rea_abhaengigkeiten_bei_frischer_installation():
    text = read(INSTALL)
    assert "tshark" in text
    assert "wireshark-common" in text
    assert "command -v tshark" in text
    assert "command -v capinfos" in text
    assert "rea-tshark" in text
    assert "/usr/bin/tshark" in text
    assert "chmod 000 /usr/bin/dumpcap" in text
    assert "Live-Capture ist nicht gesperrt" in text


def test_tshark_adapter_gibt_node_die_versionsausgabe_weiter():
    text = read(INSTALL)
    assert 'out="$(mktemp)"' in text
    assert '/usr/bin/tshark "$@"' in text
    assert 'cat "$out"' in text
    assert "ulimit -f 131072" in text
    assert 'kill "$child"' in text
    assert 'trap' in text


def test_frischer_container_bekommt_alle_laufzeitpakete_vor_den_werkzeugen():
    """Das Ubuntu-Minimalimage enthält weder xz/unzip/java noch Binutils."""
    text = read(INSTALL)
    assert "install_container_dependencies" in text
    assert text.index("install_container_dependencies") < text.index("install_tools")
    for package in (
        "xz-utils", "unzip", "openjdk-21-jre-headless", "file", "binutils",
        "python3", "ca-certificates", "gcc", "pkg-config", "libfontconfig1-dev",
        "squashfs-tools", "p7zip-full", "cpio", "device-tree-compiler", "yara",
    ):
        assert package in text, f"Containerpaket fehlt: {package}"
    assert "--no-install-recommends" in text


def test_container_abhaengigkeiten_werden_nach_der_installation_geprueft():
    text = read(INSTALL)
    for command in ("xz", "unzip", "java", "file", "objdump", "readelf", "strings",
                    "python3", "gcc", "pkg-config", "mksquashfs", "unsquashfs",
                    "7z", "cpio", "dtc", "yara"):
        assert f"command -v {command}" in text, f"Preflight fehlt: {command}"


def _resolve_architecture(architecture: str) -> dict[str, str]:
    script = r'''
source "$1"
incus() { printf '%s\n' "$FAKE_ARCH"; }
resolve_architecture
printf '%s\n' \
  "$NODE_TARBALL" "$NODE_URL" "$NODE_SHA256" \
  "$RUST_TARBALL" "$RUST_URL" "$RUST_SHA256" \
  "$SASQUATCH_FILE" "$SASQUATCH_URL" "$SASQUATCH_SHA256"
'''
    env = {**os.environ, "FAKE_ARCH": architecture}
    result = subprocess.run(
        ["bash", "-c", script, "test-resolve", str(INSTALL)],
        check=True, capture_output=True, text=True, env=env,
    )
    keys = (
        "node_file", "node_url", "node_sha256",
        "rust_file", "rust_url", "rust_sha256",
        "sasquatch_file", "sasquatch_url", "sasquatch_sha256",
    )
    return dict(zip(keys, result.stdout.splitlines(), strict=True))


def test_architekturabhaengige_quellen_und_pruefsummen_sind_korrekt_zugeordnet():
    expected = {
        "x86_64": {
            "node_file": "node-v24.22.2-linux-x64.tar.xz",
            "node_sha256": "48cc0e21e048790e54c0cf5749c2725005313d652651c40b7a21feb9697aaf75",
            "rust_file": "rust-1.81.0-x86_64-unknown-linux-gnu.tar.xz",
            "rust_sha256": "1a9ee8caaa18a3e433fef93cea8a55dc1ebd478ed761b2fef69d4565f9d00e7f",
            "sasquatch_file": "sasquatch_1.0_amd64.deb",
            "sasquatch_sha256": "bb211daf90069a43b7d5e76f136766a8542a5328015773e9b8be87541b307b60",
        },
        "aarch64": {
            "node_file": "node-v24.22.2-linux-arm64.tar.xz",
            "node_sha256": "eb187837a2230d4047161ac0be008584e16b46f726e9c9490ee35dc6b17d9ba8",
            "rust_file": "rust-1.81.0-aarch64-unknown-linux-gnu.tar.xz",
            "rust_sha256": "5cd65b0a2724e4193a5c4ba79f0687f8c11d52c2d58ee35bc7ce5958a3cc8dc2",
            "sasquatch_file": "sasquatch_1.0_arm64.deb",
            "sasquatch_sha256": "fb281906a25667414e8b6aff96b49ceb227519122a7844bbc8166f2b6a59554a",
        },
    }
    for architecture, wanted in expected.items():
        resolved = _resolve_architecture(architecture)
        for key, value in wanted.items():
            assert resolved[key] == value
        assert resolved["node_url"].endswith(resolved["node_file"])
        assert resolved["rust_url"].endswith(resolved["rust_file"])
        assert resolved["sasquatch_url"].endswith(resolved["sasquatch_file"])
        for key in ("node_sha256", "rust_sha256", "sasquatch_sha256"):
            assert re.fullmatch(r"[0-9a-f]{64}", resolved[key])

    text = read(INSTALL)
    assert 'mv "/opt/${1%.tar.xz}" /opt/node' in text
    assert "Nicht unterstuetzte Architektur" in text


def test_analyse_laeuft_offline():
    """Der Adapter schaltet das Netz vor der Analyse ab."""
    from backend import runtime

    text = read(MODULE_DIR / "backend" / "runtime.py")
    assert "disable_network" in text
    assert "enable_network" not in text
    assert runtime.CONTAINER_NAME == "hh-zerlegewerkstatt"


def test_installer_entfernt_das_netz_auch_bei_einem_fehler():
    """Das nur fuer Downloads benoetigte eth0 darf nach install.sh nie bleiben."""
    text = read(INSTALL)
    main = text[text.index("main() {"):]
    assert "disable_network()" in text
    assert "trap disable_network EXIT" in main
    assert main.index("trap disable_network EXIT") < main.index("create_container")
    assert main.index("trap disable_network EXIT") < main.index("start_container")
    assert main.index("trap disable_network EXIT") < main.index("ensure_install_network")
    assert main.index("verify_install") < main.rindex("disable_network")
    assert main.rindex("disable_network") < main.index("trap - EXIT")
