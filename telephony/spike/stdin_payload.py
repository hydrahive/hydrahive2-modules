"""Shared strict stdin decoder for machine-only SIP spike entry points."""

from __future__ import annotations

import json
from typing import TextIO

from .config import ProbeTarget, SipCredentials

_MAX_INPUT_BYTES = 1024
_REQUIRED_KEYS = {"registrar", "port", "username", "password"}


class InvalidProbePayload(ValueError):
    """Raised without retaining or echoing rejected credential payloads."""


def read_probe_payload(input_stream: TextIO) -> tuple[ProbeTarget, SipCredentials]:
    raw = input_stream.read(_MAX_INPUT_BYTES + 1)
    payload: object = None
    try:
        if len(raw) > _MAX_INPUT_BYTES:
            raise InvalidProbePayload
        payload = json.loads(raw)
        if not isinstance(payload, dict) or set(payload) != _REQUIRED_KEYS:
            raise InvalidProbePayload
        if type(payload["port"]) is not int:
            raise InvalidProbePayload
        if not all(
            isinstance(payload[key], str)
            for key in ("registrar", "username", "password")
        ):
            raise InvalidProbePayload
        target = ProbeTarget(payload["registrar"], payload["port"])
        credentials = SipCredentials(payload["username"], payload["password"])
        return target, credentials
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise InvalidProbePayload from exc
    finally:
        raw = ""
        payload = None
