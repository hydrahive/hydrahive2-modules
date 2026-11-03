"""Isolierter Analyseadapter: Positivliste, Zeitlimit, Abbruch, Aufräumen."""
from __future__ import annotations

import json
import time

import pytest

from backend import runtime
from backend.runtime import IncusRuntime, RuntimeError_, _run


class FakeRunner:
    """Aufzeichnung aller Aufrufe statt echter Incus-Kommandos."""

    def __init__(self, *, results=None):
        self.calls: list[list[str]] = []
        self.results = results or {}

    def __call__(self, command, *, timeout=60.0, cwd=None):
        self.calls.append(list(command))
        joined = " ".join(command)
        for pattern, result in self.results.items():
            if pattern == "analysis":
                if "rea" in command:
                    return result
            elif pattern in joined:
                return result
        return self._default(command)

    def _default(self, command):
        """Antworten, die einen laufenden Container mit Netz vortaeuschen."""
        if command[:2] == ["incus", "info"]:
            return ok("Status: RUNNING")
        if "config" in command and "device" in command and "list" in command:
            return ok("eth0 (nic)")
        if command[:2] == ["incus", "list"]:
            return ok("RUNNING")
        if command[:2] == ["incus", "start"]:
            return ok("")
        return ok()

    def analysis_call(self):
        """Den Aufruf finden, der die eigentliche Analyse startet."""
        for call in self.calls:
            if "rea" in call:
                return call
        return None

def ok(stdout: str = "") -> runtime.CommandResult:
    return runtime.CommandResult(returncode=0, stdout=stdout, stderr="")


def test_analyse_benutzt_nur_die_positivliste(tmp_path):
    runner = FakeRunner()
    adapter = IncusRuntime(runner=runner)
    artifact = tmp_path / "a.pe"
    artifact.write_bytes(b"MZ")

    adapter.analyze(analysis_type="inspect-managed-artifact", artifact=artifact,
                    artifact_kind="pe", token="t1")

    exec_calls = [call for call in runner.calls if call[:2] == ["incus", "exec"]]
    assert exec_calls, "es wurde nichts ausgefuehrt"
    for call in exec_calls:
        assert not any(char in " ".join(call) for char in ";|&$`<>")
    analyse_calls = [call for call in exec_calls if "rea" in call]
    assert analyse_calls, "die REA-Analyse wurde nicht gestartet"


def test_analyse_laeuft_als_unprivilegierter_rea_benutzer(tmp_path):
    runner = FakeRunner()
    adapter = IncusRuntime(runner=runner)
    artifact = tmp_path / "a.pe"
    artifact.write_bytes(b"MZ")

    adapter.analyze(analysis_type="inspect-managed-artifact", artifact=artifact,
                    artifact_kind="pe", token="t1")

    call = runner.analysis_call()
    assert call is not None
    boundary = call.index("--")
    sandbox = call[boundary + 1:call.index("rea", boundary)]
    assert sandbox[:4] == ["setpriv", "--reuid=rea", "--regid=rea", "--init-groups"]
    assert "--no-new-privs" in sandbox
    assert "--inh-caps=-all" in sandbox
    assert "--ambient-caps=-all" in sandbox
    assert "--bounding-set=-all" in sandbox
    assert sandbox[-1] == "--"


def test_pcap_bekommt_feste_wireshark_werkzeuge(tmp_path):
    runner = FakeRunner()
    adapter = IncusRuntime(runner=runner)
    artifact = tmp_path / "a.pcap"
    artifact.write_bytes(b"pcap")

    adapter.analyze(analysis_type="inspect-pcap-capture", artifact=artifact,
                    artifact_kind="pcap", token="t1")

    call = runner.analysis_call()
    assert call is not None
    assert "REA_TSHARK_COMMAND=/usr/local/bin/rea-tshark" in call
    assert "REA_CAPINFOS_COMMAND=/usr/bin/capinfos" in call


def test_firmware_bekommt_nur_den_festen_binwalk_pfad(tmp_path):
    runner = FakeRunner()
    adapter = IncusRuntime(runner=runner)
    artifact = tmp_path / "router.bin"
    artifact.write_bytes(b"firmware")

    adapter.analyze(analysis_type="inspect-firmware-regions", artifact=artifact,
                    artifact_kind="firmware", token="t1")

    call = runner.analysis_call()
    assert call is not None
    assert "REA_BINWALK_COMMAND=/opt/binwalk/bin/binwalk" in call
    assert not any(part.startswith("REA_UNBLOB_COMMAND=") for part in call)


def test_analyse_ohne_shell_und_mit_festem_provider(tmp_path):
    runner = FakeRunner()
    adapter = IncusRuntime(runner=runner)
    artifact = tmp_path / "a.pe"
    artifact.write_bytes(b"MZ")

    adapter.analyze(analysis_type="analyze-ghidra", artifact=artifact,
                    artifact_kind="pe", token="t1")

    exec_calls = [call for call in runner.calls if call[:2] == ["incus", "exec"]]
    analyse = [call for call in exec_calls if "analyze" in call][0]
    assert "bash" not in analyse
    assert analyse[analyse.index("--provider") + 1] == "ghidra"


def test_verbotener_typ_wird_vor_dem_start_abgelehnt(tmp_path):
    runner = FakeRunner()
    adapter = IncusRuntime(runner=runner)
    artifact = tmp_path / "a.apk"
    artifact.write_bytes(b"MZ")

    with pytest.raises(RuntimeError_) as error:
        adapter.analyze(analysis_type="inspect-managed-artifact", artifact=artifact,
                        artifact_kind="apk", token="t1")
    assert error.value.code == "analysis_type_not_allowed"
    assert runner.calls == []


def test_fehlende_artefaktdatei_wird_abgelehnt(tmp_path):
    runner = FakeRunner()
    adapter = IncusRuntime(runner=runner)

    with pytest.raises(RuntimeError_) as error:
        adapter.analyze(analysis_type="inspect-artifact", artifact=tmp_path / "weg.pe",
                        artifact_kind="pe", token="t1")
    assert error.value.code == "artifact_missing"


def test_netz_wird_vor_der_analyse_entfernt_und_bleibt_aus(tmp_path):
    runner = FakeRunner()
    adapter = IncusRuntime(runner=runner)
    artifact = tmp_path / "a.pe"
    artifact.write_bytes(b"MZ")

    adapter.analyze(analysis_type="inspect-artifact", artifact=artifact,
                    artifact_kind="pe", token="t1")

    remove = [call for call in runner.calls if "remove" in call]
    add = [call for call in runner.calls if "device" in call and "add" in call]
    assert remove, "Netz wurde nicht abgeklemmt"
    assert add == [], "Netz wurde nach der Analyse wieder angeklemmt"


def test_netz_bleibt_auch_nach_einem_analysefehler_aus(tmp_path):
    runner = FakeRunner(results={"analysis": runtime.CommandResult(
        returncode=1, stdout="", stderr="kaputt")})
    adapter = IncusRuntime(runner=runner)
    artifact = tmp_path / "a.pe"
    artifact.write_bytes(b"MZ")

    with pytest.raises(RuntimeError_):
        adapter.analyze(analysis_type="inspect-artifact", artifact=artifact,
                        artifact_kind="pe", token="t1")

    add = [call for call in runner.calls if "device" in call and "add" in call]
    assert add == [], "Netz wurde nach dem Analysefehler wieder angeklemmt"


def test_netz_bleibt_auch_nach_einem_ordnerfehler_aus(tmp_path):
    runner = FakeRunner(results={"mkdir": runtime.CommandResult(
        returncode=1, stdout="", stderr="kein ordner")})
    adapter = IncusRuntime(runner=runner)
    artifact = tmp_path / "a.pe"
    artifact.write_bytes(b"MZ")

    with pytest.raises(RuntimeError_):
        adapter.analyze(analysis_type="inspect-artifact", artifact=artifact,
                        artifact_kind="pe", token="t1")

    add = [call for call in runner.calls if "device" in call and "add" in call]
    assert add == [], "Netz wurde nach dem Ordnerfehler wieder angeklemmt"


def test_arbeitsdatei_wird_dem_rea_benutzer_uebergeben(tmp_path):
    runner = FakeRunner()
    adapter = IncusRuntime(runner=runner)
    artifact = tmp_path / "a.pe"
    artifact.write_bytes(b"MZ")

    adapter.analyze(analysis_type="inspect-managed-artifact", artifact=artifact,
                    artifact_kind="pe", token="t1")

    chown = [call for call in runner.calls if "chown" in call]
    assert chown
    assert "rea:rea" in chown[-1]
    assert "/work/t1/artifact.pe" in chown[-1]


def test_arbeitsordner_wird_wieder_entfernt(tmp_path):
    runner = FakeRunner()
    adapter = IncusRuntime(runner=runner)
    artifact = tmp_path / "a.pe"
    artifact.write_bytes(b"MZ")

    adapter.analyze(analysis_type="inspect-artifact", artifact=artifact,
                    artifact_kind="pe", token="t1")

    removals = [call for call in runner.calls
                if call[:4] == ["incus", "exec", "hh-zerlegewerkstatt", "--"]
                and "rm" in call]
    assert removals, "Arbeitsordner blieb zurueck"


def test_zeitlimit_beendet_und_meldet_timeout(tmp_path):
    runner = FakeRunner(results={"analysis": runtime.CommandResult(
        returncode=-1, stdout="", stderr="", timed_out=True)})
    adapter = IncusRuntime(runner=runner)
    artifact = tmp_path / "a.pe"
    artifact.write_bytes(b"MZ")

    with pytest.raises(RuntimeError_) as error:
        adapter.analyze(analysis_type="inspect-artifact", artifact=artifact,
                        artifact_kind="pe", token="t1")
    assert error.value.code == "analysis_timeout"


def test_fehlschlag_der_analyse_wird_gemeldet(tmp_path):
    runner = FakeRunner(results={"analysis": runtime.CommandResult(
        returncode=1, stdout="", stderr="kaputt")})
    adapter = IncusRuntime(runner=runner)
    artifact = tmp_path / "a.pe"
    artifact.write_bytes(b"MZ")

    with pytest.raises(RuntimeError_) as error:
        adapter.analyze(analysis_type="inspect-artifact", artifact=artifact,
                        artifact_kind="pe", token="t1")
    assert error.value.code == "analysis_failed"


def test_ungueltige_ausgabe_wird_abgelehnt(tmp_path):
    runner = FakeRunner(results={"analysis": runtime.CommandResult(
        returncode=0, stdout="kein json", stderr="")})
    adapter = IncusRuntime(runner=runner)
    artifact = tmp_path / "a.pe"
    artifact.write_bytes(b"MZ")

    with pytest.raises(RuntimeError_) as error:
        adapter.analyze(analysis_type="inspect-artifact", artifact=artifact,
                        artifact_kind="pe", token="t1")
    assert error.value.code == "analysis_output_invalid"


def test_ergebnis_wird_als_dict_geliefert(tmp_path):
    payload = {"ok": True, "evidence": []}
    runner = FakeRunner(results={"analysis": runtime.CommandResult(
        returncode=0, stdout=json.dumps(payload), stderr="")})
    adapter = IncusRuntime(runner=runner)
    artifact = tmp_path / "a.pe"
    artifact.write_bytes(b"MZ")

    result, _run_result = adapter.analyze(
        analysis_type="inspect-artifact", artifact=artifact,
        artifact_kind="pe", token="t1")
    assert result == payload


def test_fehlender_container_wird_gemeldet():
    adapter = IncusRuntime(runner=lambda *a, **k: runtime.CommandResult(
        returncode=1, stdout="", stderr="no container"))
    status = adapter.status()
    assert status.available is False
    assert status.code == "runtime_container_missing"


def test_ausgabegrenze_greift():
    """Sehr grosse Ausgabe wird gekuerzt."""
    result = _run(["python3", "-c", "import sys; sys.stdout.write('x'*1000000)"],
                  timeout=30)
    assert len(result.stdout) <= runtime.MAX_OUTPUT_BYTES


def test_zeitlimit_beendet_die_prozessgruppe():
    """Nach dem Zeitlimit laeuft kein Prozess mehr."""
    start = time.monotonic()
    result = _run(["sleep", "30"], timeout=1)
    assert result.timed_out is True
    assert time.monotonic() - start < 15
