from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
import subprocess

import pytest

from spike import incoming_runtime
from spike.config import ProbeTarget, SipCredentials
from spike.incoming_probe import IncomingOutcome, drive_incoming_call


class FakeChannel:
    def __init__(self, messages: Iterable[dict[str, object]]) -> None:
        self.messages = iter(messages)
        self.commands: list[tuple[str, str, str]] = []

    def send_command(self, command: str, params: str, token: str) -> None:
        self.commands.append((command, params, token))

    def receive(self, timeout_seconds: float) -> dict[str, object]:
        assert 0 < timeout_seconds <= 45
        try:
            return next(self.messages)
        except StopIteration as exc:
            raise TimeoutError from exc


def _event(event_type: str, **values: object) -> dict[str, object]:
    return {"event": True, "type": event_type, **values}


def test_incoming_probe_registers_answers_sendonly_plays_tone_and_hangs_up() -> None:
    channel = FakeChannel(
        [
            {"response": True, "ok": True, "token": "register", "data": ""},
            _event("REGISTER_OK", param="200 OK", accountaor="secret account"),
            _event(
                "CALL_INCOMING",
                id="fritz-call-123@fritz.box",
                direction="incoming",
                peeruri="sip:private-caller@example.invalid",
            ),
            {"response": True, "ok": True, "token": "answer", "data": ""},
            _event(
                "CALL_ESTABLISHED",
                id="fritz-call-123@fritz.box",
                direction="incoming",
            ),
            {
                "response": True,
                "ok": True,
                "token": "media-stat",
                "data": "\n  TX: packets=198, octets=31680\n",
            },
        ]
    )
    slept: list[float] = []

    outcome = drive_incoming_call(
        channel,
        incoming_timeout_seconds=45,
        tone_seconds=3,
        sleep=slept.append,
    )

    assert outcome is IncomingOutcome.INCOMING_ANSWERED
    assert channel.commands == [
        ("uareg", "300 0", "register"),
        (
            "acceptdir",
            "audio=sendonly video=inactive callid=fritz-call-123@fritz.box",
            "answer",
        ),
        ("audio_debug", "", "media-stat"),
        ("hangup", "fritz-call-123@fritz.box", "hangup"),
    ]
    assert slept == [3]


@pytest.mark.parametrize(
    "media_response",
    [
        {
            "response": True,
            "ok": True,
            "token": "media-stat",
            "data": "\n  TX: packets=0, octets=0\n",
        },
        {
            "response": True,
            "ok": True,
            "token": "media-stat",
            "data": "unexpected output",
        },
        {"response": True, "ok": False, "token": "media-stat", "data": ""},
        None,
    ],
)
def test_incoming_probe_rejects_established_call_without_audio_tx(
    media_response: dict[str, object] | None,
) -> None:
    messages = [
        _event("REGISTER_OK"),
        _event("CALL_INCOMING", id="call123", direction="incoming"),
        {"response": True, "ok": True, "token": "answer", "data": ""},
        _event("CALL_ESTABLISHED", id="call123", direction="incoming"),
    ]
    if media_response is not None:
        messages.append(media_response)
    channel = FakeChannel(messages)

    outcome = drive_incoming_call(channel, tone_seconds=4, sleep=lambda _: None)

    assert outcome is IncomingOutcome.MEDIA_FAILED
    assert channel.commands[-2:] == [
        ("audio_debug", "", "media-stat"),
        ("hangup", "call123", "hangup"),
    ]


@pytest.mark.parametrize(
    ("parameter", "expected"),
    [
        ("401 Unauthorized", IncomingOutcome.AUTH_FAILED),
        ("403 Forbidden", IncomingOutcome.AUTH_FAILED),
        ("500 Registration failed", IncomingOutcome.REGISTRATION_FAILED),
    ],
)
def test_incoming_probe_maps_registration_failure_without_returning_raw_details(
    parameter: str, expected: IncomingOutcome
) -> None:
    channel = FakeChannel([_event("REGISTER_FAIL", param=parameter)])

    assert drive_incoming_call(channel) is expected
    assert channel.commands == [("uareg", "300 0", "register")]


def test_incoming_probe_times_out_when_no_call_arrives() -> None:
    channel = FakeChannel([_event("REGISTER_OK")])

    assert drive_incoming_call(channel) is IncomingOutcome.NO_INCOMING_CALL


def test_incoming_probe_reports_caller_cancelled_before_established() -> None:
    channel = FakeChannel(
        [
            _event("REGISTER_OK"),
            _event("CALL_INCOMING", id="call123", direction="incoming"),
            _event("CALL_CLOSED", id="call123", direction="incoming"),
        ]
    )

    assert drive_incoming_call(channel) is IncomingOutcome.CALLER_CANCELLED


def test_incoming_probe_rejects_remote_call_id_command_injection() -> None:
    channel = FakeChannel(
        [
            _event("REGISTER_OK"),
            _event(
                "CALL_INCOMING",
                id="call123 hangupall all",
                direction="incoming",
            ),
        ]
    )

    assert drive_incoming_call(channel) is IncomingOutcome.ANSWER_FAILED
    assert channel.commands == [("uareg", "300 0", "register")]


def test_incoming_probe_ignores_non_incoming_call_events() -> None:
    channel = FakeChannel(
        [
            _event("REGISTER_OK"),
            _event("CALL_INCOMING", id="call123", direction="outgoing"),
        ]
    )

    assert drive_incoming_call(channel) is IncomingOutcome.NO_INCOMING_CALL


def test_run_incoming_probe_suppresses_logs_and_keeps_secrets_out_of_args(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    captured: dict[str, object] = {}

    class Process:
        pid = 123

        def wait(self, timeout: int) -> int:
            captured["wait_timeout"] = timeout
            return 0

    class Channel:
        commands: list[tuple[str, str, str]] = []

        def send_command(self, command: str, params: str, token: str) -> None:
            self.commands.append((command, params, token))

        def close(self) -> None:
            captured["closed"] = True

    channel = Channel()

    def fake_popen(command: list[str], **kwargs: object) -> Process:
        captured["command"] = command
        captured["kwargs"] = kwargs
        return Process()

    monkeypatch.setattr(subprocess, "Popen", fake_popen)
    monkeypatch.setattr(
        incoming_runtime.BaresipControlClient,
        "connect",
        lambda **_kwargs: channel,
    )
    monkeypatch.setattr(
        incoming_runtime,
        "drive_incoming_call",
        lambda *_args, **_kwargs: IncomingOutcome.INCOMING_ANSWERED,
    )

    report = incoming_runtime.run_incoming_probe(
        target=ProbeTarget(registrar="192.168.3.1"),
        credentials=SipCredentials(
            username="phone-user-01", password="TopSecretPhonePassword"
        ),
        binary=Path("/opt/baresip/bin/baresip"),
        module_dir=Path("/opt/baresip/lib/baresip/modules"),
        temp_parent=tmp_path,
    )

    command = " ".join(captured["command"])
    kwargs = captured["kwargs"]
    assert report.outcome is IncomingOutcome.INCOMING_ANSWERED
    assert "phone-user-01" not in command
    assert "TopSecretPhonePassword" not in command
    assert kwargs["stdin"] is subprocess.DEVNULL
    assert kwargs["stdout"] is subprocess.DEVNULL
    assert kwargs["stderr"] is subprocess.DEVNULL
    assert kwargs["start_new_session"] is True
    assert channel.commands[-3:] == [
        ("hangupall", "all", "cleanup-calls"),
        ("uareg", "0 0", "cleanup-register"),
        ("quit", "", "cleanup-quit"),
    ]
    assert captured["closed"] is True
