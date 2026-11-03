"""Feste Analysetypen und Befehlspositivliste der Zerlege-Werkstatt.

Der Aufrufer bestimmt einen Analysetyp, nie einen Befehl. Jeder Typ ist auf
eine feste REA-Anweisung abgebildet. Es gibt keinen Weg, ein beliebiges
REA-Unterkommando, eine Option oder ein Argument durchzureichen.

Die Liste folgt SPEC §7. Befehle, die ein Ziel ausfuehren wuerden, sind
absichtlich nicht enthalten.
"""
from __future__ import annotations

from typing import Literal

AnalysisType = Literal[
    "inspect-artifact",
    "inspect-android-package",
    "inspect-managed-artifact",
    "inspect-managed-members",
    "inspect-pcap-capture",
    "inspect-byte-entropy",
    "inspect-native-exports",
    "inspect-pe-imports",
    "inspect-pe-resources",
    "inspect-pe-load-config",
    "inspect-pe-certificates",
    "inspect-elf-notes",
    "inspect-go-binary",
    "inspect-rust-binary",
    "inspect-kernel-module",
    "inspect-apk-signature",
    "inspect-firmware-regions",
    "analyze-ghidra",
]

#: Analysetyp -> REA-Unterkommando. Nur diese Zuordnung wird ausgefuehrt.
COMMANDS: dict[str, str] = {
    "inspect-artifact": "inspect-artifact",
    "inspect-android-package": "inspect-android-package",
    "inspect-managed-artifact": "inspect-managed-artifact",
    "inspect-managed-members": "inspect-managed-members",
    "inspect-pcap-capture": "inspect-pcap-capture",
    "inspect-byte-entropy": "inspect-byte-entropy",
    "inspect-native-exports": "inspect-native-exports",
    "inspect-pe-imports": "inspect-pe-imports",
    "inspect-pe-resources": "inspect-pe-resources",
    "inspect-pe-load-config": "inspect-pe-load-config",
    "inspect-pe-certificates": "inspect-pe-certificates",
    "inspect-elf-notes": "inspect-elf-notes",
    "inspect-go-binary": "inspect-go-binary",
    "inspect-rust-binary": "inspect-rust-binary",
    "inspect-kernel-module": "inspect-kernel-module",
    "inspect-apk-signature": "inspect-apk-signature",
    "inspect-firmware-regions": "inspect-firmware-regions",
    "analyze-ghidra": "analyze",
}

#: Analysetyp -> Artefakttypen, fuer die der Typ sinnvoll ist.
ALLOWED_KINDS: dict[str, frozenset[str]] = {
    "inspect-artifact": frozenset({"pe", "apk", "elf", "pcap", "pcapng", "firmware"}),
    "inspect-android-package": frozenset({"apk"}),
    "inspect-managed-artifact": frozenset({"pe"}),
    "inspect-managed-members": frozenset({"pe"}),
    "inspect-pcap-capture": frozenset({"pcap", "pcapng"}),
    "inspect-byte-entropy": frozenset({"pe", "apk", "elf", "pcap", "pcapng", "firmware"}),
    "inspect-native-exports": frozenset({"pe", "elf"}),
    "inspect-pe-imports": frozenset({"pe"}),
    "inspect-pe-resources": frozenset({"pe"}),
    "inspect-pe-load-config": frozenset({"pe"}),
    "inspect-pe-certificates": frozenset({"pe"}),
    "inspect-elf-notes": frozenset({"elf"}),
    "inspect-go-binary": frozenset({"pe", "elf"}),
    "inspect-rust-binary": frozenset({"pe", "elf"}),
    "inspect-kernel-module": frozenset({"elf"}),
    "inspect-apk-signature": frozenset({"apk"}),
    "inspect-firmware-regions": frozenset({"firmware"}),
    "analyze-ghidra": frozenset({"pe", "elf", "firmware"}),
}

#: Zusatzargumente je Typ. Fest, keine Benutzereingabe.
#: `inspect-artifact` braucht bei --detail summary zwingend --evidence_output.
EXTRA_ARGS: dict[str, tuple[str, ...]] = {
    "inspect-artifact": ("--detail", "summary"),
    "inspect-android-package": (),
    "inspect-managed-artifact": (),
    "inspect-managed-members": ("--detail", "summary"),
    "inspect-pcap-capture": (),
    "inspect-byte-entropy": ("--block-size", "65536"),
    "inspect-native-exports": ("--detail", "summary"),
    "inspect-pe-imports": (),
    "inspect-pe-resources": (),
    "inspect-pe-load-config": (),
    "inspect-pe-certificates": (),
    "inspect-elf-notes": (),
    "inspect-go-binary": ("--detail", "summary"),
    "inspect-rust-binary": ("--detail", "summary"),
    "inspect-kernel-module": (),
    "inspect-apk-signature": ("--detail", "summary"),
    "inspect-firmware-regions": (),
    "analyze-ghidra": (),
}

#: REA verwendet leider zwei Namen fuer das Evidence-Ziel. Diese Zuordnung ist
#: fest und kann nicht durch Nutzer oder Agenten beeinflusst werden. Befehle wie
#: `inspect-firmware-regions` liefern bereits den vollstaendigen Beleg mit
#: `evidence_id` auf stdout und brauchen deshalb keine zusaetzliche Bundle-Datei.
EVIDENCE_OPTIONS: dict[str, str] = {
    "inspect-artifact": "--evidence_output",
    "inspect-managed-members": "--evidence-bundle",
    "inspect-native-exports": "--evidence_output",
    "inspect-go-binary": "--evidence_output",
    "inspect-rust-binary": "--evidence_output",
    "inspect-apk-signature": "--evidence_output",
}

#: Fester Argumentanhang, den jeder Befehl bekommt.
COMMON_ARGS: tuple[str, ...] = ("--format", "json")

#: Name des Evidence-Bundles im Arbeitsordner.
EVIDENCE_NAME = "evidence.json"


def all_types() -> tuple[str, ...]:
    """Alle erlaubten Analysetypen."""
    return tuple(COMMANDS)


def is_allowed(kind: str, analysis_type: str) -> bool:
    """Passt der Analysetyp zum Artefakttyp?"""
    return analysis_type in COMMANDS and kind in ALLOWED_KINDS.get(analysis_type, frozenset())


def build_command(analysis_type: str, *, artifact_path: str, provider: str = "ghidra",
                  workdir: str = "/work") -> list[str]:
    """Argumentliste fuer einen Analysetyp. Keine Shell, keine Benutzereingabe."""
    if analysis_type not in COMMANDS:
        raise ValueError("unknown analysis type")
    args = ["rea", COMMANDS[analysis_type]]
    if analysis_type == "analyze-ghidra":
        args += ["--provider", provider]
    args += EXTRA_ARGS.get(analysis_type, ())
    evidence_option = EVIDENCE_OPTIONS.get(analysis_type)
    if evidence_option:
        args += [evidence_option, f"{workdir}/{EVIDENCE_NAME}"]
    args += list(COMMON_ARGS)
    args.append(artifact_path)
    return args
