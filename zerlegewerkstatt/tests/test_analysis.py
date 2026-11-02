"""Befehlspositivliste: kein freier Befehl, kein Shell, kein fremder Typ."""
from __future__ import annotations

import pytest

from backend import analysis_types


def test_nur_feste_analysetypen_sind_erlaubt():
    assert set(analysis_types.all_types()) == {
        "inspect-artifact",
        "inspect-android-package",
        "inspect-managed-artifact",
        "inspect-managed-members",
        "inspect-pcap-capture",
        "analyze-ghidra",
    }


def test_befehle_enthalten_keine_shell_zeichen():
    for analysis_type in analysis_types.all_types():
        command = analysis_types.build_command(analysis_type, artifact_path="/work/a.pe")
        assert command[0] == "rea"
        assert not any(char in " ".join(command) for char in ";|&$`<>\n")


def test_unbekannter_typ_wird_abgelehnt():
    with pytest.raises(ValueError):
        analysis_types.build_command("rm -rf /", artifact_path="/work/a.pe")


def test_typ_passt_zum_artefakttyp():
    assert analysis_types.is_allowed("apk", "inspect-android-package") is True
    assert analysis_types.is_allowed("apk", "analyze-ghidra") is False
    assert analysis_types.is_allowed("pe", "inspect-managed-artifact") is True
    assert analysis_types.is_allowed("pe", "inspect-android-package") is False


def test_mitglieder_und_pcap_nur_fuer_passende_dateien():
    assert analysis_types.is_allowed("pe", "inspect-managed-members")
    assert not analysis_types.is_allowed("apk", "inspect-managed-members")
    assert analysis_types.is_allowed("pcap", "inspect-pcap-capture")
    assert analysis_types.is_allowed("pcapng", "inspect-pcap-capture")
    assert not analysis_types.is_allowed("pe", "inspect-pcap-capture")


def test_managed_members_schreibt_vollstaendiges_evidence_bundle():
    args = analysis_types.build_command("inspect-managed-members", artifact_path="/work/artifact.pe", workdir="/work")
    assert args[:2] == ["rea", "inspect-managed-members"]
    assert args[args.index("--detail") + 1] == "summary"
    assert args[args.index("--evidence-bundle") + 1] == "/work/evidence.json"
    assert args[-1] == "/work/artifact.pe"


def test_pcap_analyse_braucht_nur_die_lokale_datei():
    args = analysis_types.build_command("inspect-pcap-capture", artifact_path="/work/netz.pcapng")
    assert args == ["rea", "inspect-pcap-capture", "--format", "json", "/work/netz.pcapng"]


def test_ghidra_ist_der_feste_provider():
    command = analysis_types.build_command("analyze-ghidra", artifact_path="/work/a.pe")
    assert "--provider" in command
    assert command[command.index("--provider") + 1] == "ghidra"


def test_ausgabeformat_ist_immer_json():
    for analysis_type in analysis_types.all_types():
        command = analysis_types.build_command(analysis_type, artifact_path="/work/a.pe")
        assert command[command.index("--format") + 1] == "json"


def test_kein_befehl_fuehrt_etwas_aus():
    """Kein erlaubter Befehl darf ein Ziel starten."""
    verboten = ("run", "execute", "launch", "debug", "capture-process", "adb")
    for analysis_type in analysis_types.all_types():
        command = analysis_types.build_command(analysis_type, artifact_path="/work/a.pe")
        for part in command:
            assert not any(part.startswith(word) for word in verboten)
