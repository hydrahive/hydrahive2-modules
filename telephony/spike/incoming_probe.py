"""Bounded Gate-2 state machine for one controlled incoming SIP call."""

from __future__ import annotations

import os
import re
import signal
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from .config import (
    ProbeTarget,
    SecureIncomingBaresipConfig,
    SipCredentials,
)
from .ctrl_tcp import BaresipControlClient, ControlChannel, ControlProtocolError

_CALL_ID_PATTERN = re.compile(r"[A-Za-z0-9._~-]{1,64}\Z")


class IncomingOutcome(StrEnum):
    INCOMING_ANSWERED = "incoming_answered"
    NO_INCOMING_CALL = "no_incoming_call"
    CALLER_CANCELLED = "caller_cancelled"
    ANSWER_FAILED = "answer_failed"
    AUTH_FAILED = "auth_failed"
    REGISTRATION_FAILED = "registration_failed"
    TIMEOUT = "timeout"
    RUNTIME_UNAVAILABLE = "runtime_unavailable"


@dataclass(frozen=True, slots=True)
class IncomingReport:
    outcome: IncomingOutcome
    duration_ms: int


def drive_incoming_call(
    channel: ControlChannel,
    *,
    incoming_timeout_seconds: float = 45,
    tone_seconds: float = 3,
    sleep: Callable[[float], None] = time.sleep,
) -> IncomingOutcome:
    """Drive one registration and call without exposing raw control payloads."""
    channel.send_command("uareg", "300", "register")
    registration = _wait_for_type(
        channel,
        {"REGISTER_OK", "REGISTER_FAIL"},
        timeout_seconds=8,
    )
    if registration is None:
        return IncomingOutcome.REGISTRATION_FAILED
    if registration.get("type") == "REGISTER_FAIL":
        parameter = registration.get("param")
        normalized = parameter.lower() if isinstance(parameter, str) else ""
        if "401" in normalized or "403" in normalized or "auth" in normalized:
            return IncomingOutcome.AUTH_FAILED
        return IncomingOutcome.REGISTRATION_FAILED

    incoming_deadline = time.monotonic() + incoming_timeout_seconds
    while True:
        message = _receive_before(channel, incoming_deadline)
        if message is None:
            return IncomingOutcome.NO_INCOMING_CALL
        if message.get("type") != "CALL_INCOMING":
            continue
        if message.get("direction") != "incoming":
            continue
        call_id = message.get("id")
        if not isinstance(call_id, str) or not _CALL_ID_PATTERN.fullmatch(call_id):
            return IncomingOutcome.ANSWER_FAILED
        break

    channel.send_command(
        "acceptdir",
        f"audio=sendonly video=inactive callid={call_id}",
        "answer",
    )
    answer_deadline = time.monotonic() + 10
    while True:
        message = _receive_before(channel, answer_deadline)
        if message is None:
            return IncomingOutcome.ANSWER_FAILED
        if message.get("response") is True and message.get("token") == "answer":
            if message.get("ok") is not True:
                return IncomingOutcome.ANSWER_FAILED
            continue
        if message.get("id") != call_id:
            continue
        if message.get("type") == "CALL_CLOSED":
            return IncomingOutcome.CALLER_CANCELLED
        if message.get("type") == "CALL_ESTABLISHED":
            break

    sleep(tone_seconds)
    channel.send_command("hangup", call_id, "hangup")
    return IncomingOutcome.INCOMING_ANSWERED


def run_incoming_probe(
    *,
    target: ProbeTarget,
    credentials: SipCredentials,
    binary: Path,
    module_dir: Path,
    incoming_timeout_seconds: int = 45,
    tone_seconds: int = 3,
    temp_parent: Path | None = None,
) -> IncomingReport:
    """Run one Gate-2 attempt with no inherited logs or audio persistence."""
    if not 15 <= incoming_timeout_seconds <= 45:
        raise ValueError("incoming timeout must be between 15 and 45 seconds")
    if not 1 <= tone_seconds <= 5:
        raise ValueError("tone duration must be between 1 and 5 seconds")

    started = time.monotonic()
    outcome = IncomingOutcome.RUNTIME_UNAVAILABLE
    with SecureIncomingBaresipConfig(
        target=target,
        credentials=credentials,
        module_dir=module_dir,
        temp_parent=temp_parent,
    ) as config_dir:
        process = subprocess.Popen(
            [str(binary), "-4", "-c", "-f", str(config_dir), "-t", "70"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=None,
            start_new_session=True,
        )
        channel: BaresipControlClient | None = None
        try:
            channel = BaresipControlClient.connect(timeout_seconds=5)
            outcome = drive_incoming_call(
                channel,
                incoming_timeout_seconds=incoming_timeout_seconds,
                tone_seconds=tone_seconds,
            )
        except TimeoutError:
            outcome = IncomingOutcome.TIMEOUT
        except (OSError, ControlProtocolError):
            outcome = IncomingOutcome.RUNTIME_UNAVAILABLE
        finally:
            _best_effort_shutdown(channel, process)

    return IncomingReport(outcome=outcome, duration_ms=_elapsed_ms(started))


def _wait_for_type(
    channel: ControlChannel,
    event_types: set[str],
    *,
    timeout_seconds: float,
) -> dict[str, object] | None:
    deadline = time.monotonic() + timeout_seconds
    while True:
        message = _receive_before(channel, deadline)
        if message is None:
            return None
        if message.get("event") is True and message.get("type") in event_types:
            return message


def _receive_before(
    channel: ControlChannel, deadline: float
) -> dict[str, object] | None:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        return None
    try:
        return channel.receive(remaining)
    except TimeoutError:
        return None


def _best_effort_shutdown(
    channel: BaresipControlClient | None,
    process: subprocess.Popen[bytes],
) -> None:
    if channel is not None:
        for command, params, token in (
            ("hangupall", "all", "cleanup-calls"),
            ("uareg", "0", "cleanup-register"),
            ("quit", "", "cleanup-quit"),
        ):
            try:
                channel.send_command(command, params, token)
            except OSError:
                break
        channel.close()
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        _kill_process_group(process)


def _kill_process_group(process: subprocess.Popen[bytes]) -> None:
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except PermissionError:
        try:
            process.kill()
        except PermissionError:
            return
    except ProcessLookupError:
        return


def _elapsed_ms(started: float) -> int:
    return round((time.monotonic() - started) * 1000)
