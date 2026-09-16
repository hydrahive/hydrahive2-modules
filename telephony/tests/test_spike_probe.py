from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

import spike.probe as probe_module
from spike.config import ProbeTarget, SipCredentials
from spike.probe import ProbeOutcome, classify_registration_output, run_probe


@pytest.mark.parametrize(
    ("output", "expected"),
    [
        (
            "serreg: 1 useragent with prio 0 registered successfully!",
            ProbeOutcome.REGISTERED,
        ),
        ("401 Unauthorized\nserreg: registered successfully!", ProbeOutcome.REGISTERED),
        ("account: {0/UDP/v4} 200 OK (FRITZ!Box)", ProbeOutcome.REGISTERED),
        ("401 Unauthorized", ProbeOutcome.AUTH_FAILED),
        ("403 Forbidden", ProbeOutcome.AUTH_FAILED),
        ("authentication failed", ProbeOutcome.AUTH_FAILED),
        (
            "ua: SIP register failed: Network is unreachable",
            ProbeOutcome.REGISTRATION_FAILED,
        ),
        ("unrelated startup text", ProbeOutcome.NO_RESULT),
    ],
)
def test_classify_registration_output(output: str, expected: ProbeOutcome) -> None:
    assert classify_registration_output(output) is expected


def test_run_probe_never_places_credentials_in_process_arguments(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    captured: dict[str, object] = {}

    class FakeProcess:
        pid = 123
        returncode = 0

        def communicate(self, *, timeout: int) -> tuple[str, str]:
            captured["timeout"] = timeout
            return "serreg: 1 useragent registered successfully!", ""

    def fake_popen(command: list[str], **kwargs: object) -> FakeProcess:
        captured["command"] = command
        captured["kwargs"] = kwargs
        return FakeProcess()

    monkeypatch.setattr(subprocess, "Popen", fake_popen)
    report = run_probe(
        target=ProbeTarget(registrar="192.168.3.1"),
        credentials=SipCredentials(
            username="phone-user-01", password="TopSecretPhonePassword"
        ),
        binary=Path("/opt/baresip/bin/baresip"),
        module_dir=Path("/opt/baresip/lib/baresip/modules"),
        temp_parent=tmp_path,
    )

    assert report.outcome is ProbeOutcome.REGISTERED
    command_text = " ".join(captured["command"])
    assert "phone-user-01" not in command_text
    assert "TopSecretPhonePassword" not in command_text
    assert captured["kwargs"]["env"] is None
    assert captured["kwargs"]["start_new_session"] is True
    assert captured["timeout"] == 22


def test_probe_kill_falls_back_when_group_signal_is_denied(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    killed: list[bool] = []

    class Process:
        pid = 654

        def kill(self) -> None:
            killed.append(True)

    def denied(*_args) -> None:
        raise PermissionError

    monkeypatch.setattr(probe_module.os, "killpg", denied)

    probe_module._kill_process_group(Process())

    assert killed == [True]


def test_run_probe_kills_process_group_on_timeout_without_exposing_secrets(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: list[tuple[int, int]] = []

    class TimeoutProcess:
        pid = 456
        returncode = -9
        attempts = 0

        def communicate(self, *, timeout: int) -> tuple[str, str]:
            self.attempts += 1
            if self.attempts == 1:
                raise subprocess.TimeoutExpired(["baresip"], timeout=timeout)
            return "", ""

    monkeypatch.setattr(subprocess, "Popen", lambda *_args, **_kwargs: TimeoutProcess())
    monkeypatch.setattr(
        probe_module.os,
        "killpg",
        lambda process_group, sent_signal: calls.append((process_group, sent_signal)),
    )

    report = run_probe(
        target=ProbeTarget(registrar="192.168.3.1"),
        credentials=SipCredentials(
            username="phone-user-01", password="TopSecretPhonePassword"
        ),
        binary=Path("/opt/baresip/bin/baresip"),
        module_dir=Path("/opt/baresip/lib/baresip/modules"),
        temp_parent=tmp_path,
    )

    assert report.outcome is ProbeOutcome.TIMEOUT
    assert calls == [(456, probe_module.signal.SIGKILL)]
    assert "phone-user-01" not in repr(report)
    assert "TopSecretPhonePassword" not in repr(report)
