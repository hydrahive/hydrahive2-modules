from __future__ import annotations

import json
import subprocess

import pytest

from backend import probe_service
from backend.probe_models import ProbeOutcome, RegistrationProbeRequest


def _request() -> RegistrationProbeRequest:
    return RegistrationProbeRequest(
        registrar="192.168.3.1",
        port=5060,
        username="phone-user-01",
        password="TopSecretPhonePassword",
    )


def test_incoming_probe_uses_fixed_command_stdin_and_always_cleans_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    cleaned: list[bool] = []

    class Process:
        pid = 321
        returncode = 0

        def communicate(self, *, input: str, timeout: int) -> tuple[str, str]:
            captured["input"] = input
            captured["timeout"] = timeout
            return "incoming_answered\n", "private caller details"

    def fake_popen(command: list[str], **kwargs: object) -> Process:
        captured["command"] = command
        captured["kwargs"] = kwargs
        return Process()

    monkeypatch.setattr(subprocess, "Popen", fake_popen)
    monkeypatch.setattr(probe_service, "_cleanup_runtime", lambda: cleaned.append(True))

    outcome = probe_service.run_incoming_call_probe(_request())

    assert outcome is ProbeOutcome.INCOMING_ANSWERED
    assert captured["command"] == [
        "incus",
        "exec",
        "hh-telephony-spike",
        "--",
        "/opt/hh-telephony-spike/spike/run-stdin-incoming-probe.sh",
    ]
    assert json.loads(captured["input"])["password"] == "TopSecretPhonePassword"
    assert captured["timeout"] == 76
    assert cleaned == [True]
    assert "private caller details" not in repr(outcome)


@pytest.mark.parametrize(
    ("stdout", "expected"),
    [
        ("incoming_answered\n", ProbeOutcome.INCOMING_ANSWERED),
        ("no_incoming_call\n", ProbeOutcome.NO_INCOMING_CALL),
        ("caller_cancelled\n", ProbeOutcome.CALLER_CANCELLED),
        ("answer_failed\n", ProbeOutcome.ANSWER_FAILED),
        ("garbage with caller id\n", ProbeOutcome.RUNTIME_UNAVAILABLE),
    ],
)
def test_incoming_probe_allows_only_stable_outcomes_and_cleans(
    monkeypatch: pytest.MonkeyPatch, stdout: str, expected: ProbeOutcome
) -> None:
    cleaned: list[bool] = []

    class Process:
        pid = 123
        returncode = 0

        def communicate(self, *, input: str, timeout: int) -> tuple[str, str]:
            del input, timeout
            return stdout, "raw provider output"

    monkeypatch.setattr(subprocess, "Popen", lambda *_args, **_kwargs: Process())
    monkeypatch.setattr(probe_service, "_cleanup_runtime", lambda: cleaned.append(True))

    assert probe_service.run_incoming_call_probe(_request()) is expected
    assert cleaned == [True]


def test_incoming_probe_busy_does_not_interrupt_existing_sidecar_process(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cleaned: list[bool] = []

    class Process:
        pid = 123
        returncode = 0

        def communicate(self, *, input: str, timeout: int) -> tuple[str, str]:
            del input, timeout
            return "busy\n", ""

    monkeypatch.setattr(subprocess, "Popen", lambda *_args, **_kwargs: Process())
    monkeypatch.setattr(probe_service, "_cleanup_runtime", lambda: cleaned.append(True))

    assert probe_service.run_incoming_call_probe(_request()) is ProbeOutcome.BUSY
    assert cleaned == []
