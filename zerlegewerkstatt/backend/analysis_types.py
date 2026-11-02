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
    "analyze-ghidra",
]

#: Analysetyp -> REA-Unterkommando. Nur diese Zuordnung wird ausgefuehrt.
COMMANDS: dict[str, str] = {
    "inspect-artifact": "inspect-artifact",
    "inspect-android-package": "inspect-android-package",
    "inspect-managed-artifact": "inspect-managed-artifact",
    "analyze-ghidra": "analyze",
}

#: Analysetyp -> Artefakttypen, fuer die der Typ sinnvoll ist.
ALLOWED_KINDS: dict[str, frozenset[str]] = {
    "inspect-artifact": frozenset({"pe", "apk", "elf", "pcap", "pcapng", "firmware"}),
    "inspect-android-package": frozenset({"apk"}),
    "inspect-managed-artifact": frozenset({"pe"}),
    "analyze-ghidra": frozenset({"pe", "elf", "firmware"}),
}

#: Zusatzargumente je Typ. Fest, keine Benutzereingabe.
#: `inspect-artifact` braucht bei --detail summary zwingend --evidence_output.
EXTRA_ARGS: dict[str, tuple[str, ...]] = {
    "inspect-artifact": ("--detail", "summary"),
    "inspect-android-package": (),
    "inspect-managed-artifact": (),
    "analyze-ghidra": (),
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
    if analysis_type == "inspect-artifact":
        # --detail summary verlangt zwingend ein Ziel fuer das Evidence-Bundle.
        args += ["--evidence_output", f"{workdir}/{EVIDENCE_NAME}"]
    args += list(COMMON_ARGS)
    args.append(artifact_path)
    return args
