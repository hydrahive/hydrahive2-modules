"""Bounded client for Baresip's loopback-only ctrl_tcp netstring protocol."""

from __future__ import annotations

import json
import socket
import time
from collections import deque
from collections.abc import Callable
from typing import Protocol

_MAX_PAYLOAD_BYTES = 8192
_MAX_LENGTH_DIGITS = 6


class ControlProtocolError(RuntimeError):
    """Raised for malformed, oversized, or truncated control messages."""


class ControlChannel(Protocol):
    def send_command(self, command: str, params: str, token: str) -> None: ...

    def receive(self, timeout_seconds: float) -> dict[str, object]: ...


class NetstringBuffer:
    """Incrementally decode bounded JSON-object netstrings."""

    def __init__(self, max_payload_bytes: int = _MAX_PAYLOAD_BYTES) -> None:
        self._buffer = bytearray()
        self._max_payload_bytes = max_payload_bytes

    def feed(self, data: bytes) -> list[dict[str, object]]:
        self._buffer.extend(data)
        messages: list[dict[str, object]] = []
        while self._buffer:
            separator = self._buffer.find(b":")
            if separator < 0:
                if len(self._buffer) > _MAX_LENGTH_DIGITS:
                    raise ControlProtocolError("invalid netstring length")
                break
            prefix = bytes(self._buffer[:separator])
            if not prefix or len(prefix) > _MAX_LENGTH_DIGITS or not prefix.isdigit():
                raise ControlProtocolError("invalid netstring length")
            payload_length = int(prefix)
            if payload_length > self._max_payload_bytes:
                raise ControlProtocolError("control payload too large")
            frame_length = separator + 1 + payload_length + 1
            if len(self._buffer) < frame_length:
                break
            payload_start = separator + 1
            payload_end = payload_start + payload_length
            if self._buffer[payload_end] != ord(","):
                raise ControlProtocolError("invalid netstring terminator")
            payload = bytes(self._buffer[payload_start:payload_end])
            del self._buffer[:frame_length]
            try:
                message = json.loads(payload)
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ControlProtocolError("invalid control JSON") from exc
            if not isinstance(message, dict):
                raise ControlProtocolError("control message must be an object")
            messages.append(message)
        return messages


def encode_message(payload: dict[str, object]) -> bytes:
    """Encode one compact JSON object as a netstring."""
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode()
    if len(body) > _MAX_PAYLOAD_BYTES:
        raise ControlProtocolError("control payload too large")
    return str(len(body)).encode() + b":" + body + b","


class BaresipControlClient:
    """Single loopback ctrl_tcp connection with bounded reads."""

    def __init__(self, connection: socket.socket) -> None:
        self._connection = connection
        self._parser = NetstringBuffer()
        self._pending: deque[dict[str, object]] = deque()

    @classmethod
    def connect(
        cls,
        *,
        host: str = "127.0.0.1",
        port: int = 4444,
        timeout_seconds: float = 5,
        connector: Callable[..., socket.socket] = socket.create_connection,
    ) -> BaresipControlClient:
        deadline = time.monotonic() + timeout_seconds
        while True:
            try:
                connection = connector((host, port), timeout=0.5)
                return cls(connection)
            except OSError as exc:
                if time.monotonic() >= deadline:
                    raise TimeoutError("Baresip control socket unavailable") from exc
                time.sleep(0.05)

    def send_command(self, command: str, params: str, token: str) -> None:
        self._connection.sendall(
            encode_message({"command": command, "params": params, "token": token})
        )

    def receive(self, timeout_seconds: float) -> dict[str, object]:
        if self._pending:
            return self._pending.popleft()
        deadline = time.monotonic() + timeout_seconds
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError
            self._connection.settimeout(remaining)
            try:
                data = self._connection.recv(4096)
            except socket.timeout as exc:
                raise TimeoutError from exc
            if not data:
                raise ControlProtocolError("control connection closed")
            self._pending.extend(self._parser.feed(data))
            if self._pending:
                return self._pending.popleft()

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> BaresipControlClient:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()
