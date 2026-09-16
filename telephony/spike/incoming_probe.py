"""Bounded Gate-2 state machine for one controlled incoming SIP call."""

from __future__ import annotations

import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

from .ctrl_tcp import ControlChannel

# RFC 3261 Call-ID word subset; excludes whitespace and '=' so the value cannot
# escape the single ctrl_tcp callid parameter.
_CALL_ID_WORD = r"[A-Za-z0-9.!%*_+`'~()-]+"
_CALL_ID_PATTERN = re.compile(
    rf"(?=.{{1,255}}\Z){_CALL_ID_WORD}(?:@{_CALL_ID_WORD})?\Z"
)


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
    channel.send_command("uareg", "300 0", "register")
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
