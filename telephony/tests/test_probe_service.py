from __future__ import annotations

import json
import signal
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


def test_probe_service_passes_secrets_only_over_stdin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class Process:
        pid = 123
        returncode = 0

        def communicate(self, *, input: str, timeout: int) -> tuple[str, str]:
            captured["input"] = input
            captured["timeout"] = timeout
            return "registered\n", ""

    def fake_popen(command: list[str], **kwargs: object) -> Process:
        captured["command"] = command
        captured["kwargs"] = kwargs
        return Process()

    monkeypatch.setenv("GITHUB_TOKEN", "TopSecretInheritedToken")
    monkeypatch.setattr(subprocess, "Popen", fake_popen)

    outcome = probe_service.run_registration_probe(_request())

    assert outcome is ProbeOutcome.REGISTERED
    command = " ".join(captured["command"])
    kwargs = captured["kwargs"]
    assert "phone-user-01" not in command
    assert "TopSecretPhonePassword" not in command
    assert "phone-user-01" not in json.dumps(kwargs)
    assert "TopSecretPhonePassword" not in json.dumps(kwargs)
    assert "TopSecretInheritedToken" not in json.dumps(kwargs)
    assert json.loads(captured["input"])["password"] == "TopSecretPhonePassword"
    assert kwargs["shell"] is False
    assert kwargs["start_new_session"] is True
    assert captured["timeout"] == 12


@pytest.mark.parametrize(
    ("stdout", "expected"),
    [
        ("registered\n", ProbeOutcome.REGISTERED),
        ("auth_failed\n", ProbeOutcome.AUTH_FAILED),
        ("registration_failed\n", ProbeOutcome.REGISTRATION_FAILED),
        ("timeout\n", ProbeOutcome.TIMEOUT),
        ("busy\n", ProbeOutcome.BUSY),
        ("garbage\n", ProbeOutcome.RUNTIME_UNAVAILABLE),
    ],
)
def test_probe_service_allows_only_known_outcomes(
    monkeypatch: pytest.MonkeyPatch, stdout: str, expected: ProbeOutcome
) -> None:
    monkeypatch.setattr(probe_service, "_cleanup_runtime", lambda: None)

    class Process:
        pid = 123
        returncode = 0

        def communicate(self, *, input: str, timeout: int) -> tuple[str, str]:
            del input, timeout
            return stdout, "provider details must not escape"

    monkeypatch.setattr(subprocess, "Popen", lambda *_args, **_kwargs: Process())

    assert probe_service.run_registration_probe(_request()) is expected


def test_probe_service_returns_busy_without_starting_process(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class BusyLock:
        def acquire(self, blocking: bool) -> bool:
            assert blocking is False
            return False

    monkeypatch.setattr(probe_service, "_PROBE_LOCK", BusyLock())
    monkeypatch.setattr(
        subprocess,
        "Popen",
        lambda *_args, **_kwargs: pytest.fail("must not start a second process"),
    )

    assert probe_service.run_registration_probe(_request()) is ProbeOutcome.BUSY


def test_probe_service_kills_process_group_after_hard_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    killed: list[tuple[int, signal.Signals]] = []
    cleaned: list[bool] = []

    class Process:
        pid = 789
        returncode = -9

        def communicate(self, *, input: str, timeout: int) -> tuple[str, str]:
            del input, timeout
            raise subprocess.TimeoutExpired(["incus"], 30)

    monkeypatch.setattr(subprocess, "Popen", lambda *_args, **_kwargs: Process())
    monkeypatch.setattr(
        probe_service.os,
        "killpg",
        lambda process_group, sent_signal: killed.append((process_group, sent_signal)),
    )
    monkeypatch.setattr(
        probe_service,
        "_cleanup_runtime",
        lambda: cleaned.append(True),
    )

    outcome = probe_service.run_registration_probe(_request())

    assert outcome is ProbeOutcome.TIMEOUT
    assert killed == [(789, signal.SIGKILL)]
    assert cleaned == [True]


def test_probe_service_falls_back_to_direct_kill_when_group_kill_is_denied(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    killed: list[bool] = []

    class Process:
        pid = 987

        def kill(self) -> None:
            killed.append(True)

    def denied(*_args) -> None:
        raise PermissionError

    monkeypatch.setattr(probe_service.os, "killpg", denied)

    probe_service._kill_process_group(Process())

    assert killed == [True]


def test_probe_cleanup_restarts_only_the_dedicated_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    commands: list[list[str]] = []

    def fake_run(command: list[str], **_kwargs):
        commands.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(subprocess, "run", fake_run)

    probe_service._cleanup_runtime()

    assert commands == [
        ["incus", "stop", "--force", "hh-telephony-spike"],
        ["incus", "start", "hh-telephony-spike"],
    ]


def test_probe_service_maps_missing_runtime_without_internal_details(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        subprocess,
        "Popen",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            FileNotFoundError("secret path")
        ),
    )

    assert (
        probe_service.run_registration_probe(_request())
        is ProbeOutcome.RUNTIME_UNAVAILABLE
    )
