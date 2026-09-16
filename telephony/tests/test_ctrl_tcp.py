from __future__ import annotations

import json

import pytest

from spike.ctrl_tcp import ControlProtocolError, NetstringBuffer, encode_message


def test_encode_message_uses_compact_netstring_json() -> None:
    payload = {"command": "uareg", "params": "300", "token": "register"}

    encoded = encode_message(payload)
    body = json.dumps(payload, separators=(",", ":")).encode()

    assert encoded == str(len(body)).encode() + b":" + body + b","


def test_netstring_buffer_accepts_fragmented_message() -> None:
    parser = NetstringBuffer()
    encoded = encode_message({"event": True, "type": "REGISTER_OK"})

    assert parser.feed(encoded[:4]) == []
    assert parser.feed(encoded[4:9]) == []
    assert parser.feed(encoded[9:]) == [{"event": True, "type": "REGISTER_OK"}]


def test_netstring_buffer_returns_multiple_messages() -> None:
    parser = NetstringBuffer()

    messages = parser.feed(
        encode_message({"type": "CALL_INCOMING"})
        + encode_message({"type": "CALL_ESTABLISHED"})
    )

    assert [message["type"] for message in messages] == [
        "CALL_INCOMING",
        "CALL_ESTABLISHED",
    ]


@pytest.mark.parametrize(
    "payload",
    [
        b"x:{} ,",
        b"4:{}xx;",
        b"2:[],",
        b"3:{x},",
    ],
)
def test_netstring_buffer_rejects_invalid_frames(payload: bytes) -> None:
    parser = NetstringBuffer()

    with pytest.raises(ControlProtocolError):
        parser.feed(payload)


def test_netstring_buffer_rejects_payload_above_limit() -> None:
    parser = NetstringBuffer(max_payload_bytes=32)

    with pytest.raises(ControlProtocolError, match="too large"):
        parser.feed(b"33:" + b"x" * 33 + b",")
