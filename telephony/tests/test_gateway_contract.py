"""Transportneutraler Gatewayvertrag — ohne Netzwerk, SIP oder echte Secrets."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from uuid import UUID

import pytest
from backend.gateway import (
    CallDirection,
    CallRef,
    ConnectionRef,
    ConnectionSpec,
    DialRequest,
    EventKind,
    FakeTelephonyGateway,
    GatewayError,
    GatewayEvent,
    SpeakRequest,
    TelephonyGateway,
    TransportKind,
)
from pydantic import ValidationError

PROJECT_ID = UUID("10000000-0000-4000-8000-000000000001")
OTHER_PROJECT_ID = UUID("20000000-0000-4000-8000-000000000002")
CONNECTION_ID = UUID("30000000-0000-4000-8000-000000000003")
CALL_ID = UUID("40000000-0000-4000-8000-000000000004")
ATTEMPT_ID = UUID("50000000-0000-4000-8000-000000000005")
SECRET = "sip-password-that-must-never-leak"


def connection_spec() -> ConnectionSpec:
    return ConnectionSpec(
        project_id=PROJECT_ID,
        connection_id=CONNECTION_ID,
        registrar="fritz.box",
        port=5060,
        transport=TransportKind.UDP,
        username="hydrahive-phone",
        password=SECRET,
    )


def outbound_call(*, call_id: UUID = CALL_ID, attempt_id: UUID = ATTEMPT_ID) -> CallRef:
    return CallRef(
        project_id=PROJECT_ID,
        connection_id=CONNECTION_ID,
        call_id=call_id,
        attempt_id=attempt_id,
        direction=CallDirection.OUTBOUND,
    )


def test_connection_credentials_are_redacted_from_repr_and_json() -> None:
    connection = connection_spec()

    assert SECRET not in repr(connection)
    assert SECRET not in connection.model_dump_json()
    assert "hydrahive-phone" not in repr(connection)
    assert "hydrahive-phone" not in connection.model_dump_json()


@pytest.mark.parametrize("registrar", ["", "https://fritz.box", "fritz.box/path", "bad host"])
def test_connection_rejects_non_host_registrars(registrar: str) -> None:
    with pytest.raises(ValidationError):
        ConnectionSpec(
            project_id=PROJECT_ID,
            connection_id=CONNECTION_ID,
            registrar=registrar,
            username="phone",
            password=SECRET,
        )


def test_contract_models_reject_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        ConnectionRef(
            project_id=PROJECT_ID,
            connection_id=CONNECTION_ID,
            unexpected=True,
        )


def test_fake_satisfies_runtime_gateway_protocol() -> None:
    assert isinstance(FakeTelephonyGateway(), TelephonyGateway)


@pytest.mark.asyncio
async def test_fake_health_never_claims_live_telephony() -> None:
    health = await FakeTelephonyGateway().health()

    assert health.ready is True
    assert health.implementation == "fake"
    assert health.live_telephony_verified is False


@pytest.mark.asyncio
async def test_probe_does_not_register_or_retain_credentials() -> None:
    gateway = FakeTelephonyGateway()
    spec = connection_spec()

    probe = await gateway.probe(spec)

    assert probe.reachable is True
    assert probe.authenticated is True
    assert gateway.registered_connections == ()
    assert SECRET not in repr(gateway)


@pytest.mark.asyncio
async def test_dial_requires_a_registered_connection() -> None:
    gateway = FakeTelephonyGateway()
    request = DialRequest(call=outbound_call(), to_e164="+49301234567")

    with pytest.raises(GatewayError, match="connection_not_registered") as raised:
        await gateway.dial(request)

    assert raised.value.code == "connection_not_registered"
    assert raised.value.retryable is True


@pytest.mark.asyncio
async def test_dial_is_idempotent_for_the_same_attempt() -> None:
    gateway = FakeTelephonyGateway()
    await gateway.register(connection_spec())
    request = DialRequest(call=outbound_call(), to_e164="+49301234567")

    first = await gateway.dial(request)
    second = await gateway.dial(request)

    assert first == second == request.call
    events = gateway.drain_events()
    assert [event.kind for event in events] == [EventKind.DIALING]
    assert events[0].sequence == 1
    assert events[0].call == request.call


@pytest.mark.asyncio
async def test_attempt_id_cannot_be_reused_for_another_call() -> None:
    gateway = FakeTelephonyGateway()
    await gateway.register(connection_spec())
    first = DialRequest(call=outbound_call(), to_e164="+49301234567")
    conflicting = DialRequest(
        call=outbound_call(call_id=UUID("60000000-0000-4000-8000-000000000006")),
        to_e164="+49307654321",
    )
    await gateway.dial(first)

    with pytest.raises(GatewayError, match="attempt_conflict") as raised:
        await gateway.dial(conflicting)

    assert raised.value.code == "attempt_conflict"
    assert raised.value.retryable is False


@pytest.mark.asyncio
async def test_incoming_call_flow_emits_monotone_identity_bound_events() -> None:
    gateway = FakeTelephonyGateway()
    await gateway.register(connection_spec())
    call = CallRef(
        project_id=PROJECT_ID,
        connection_id=CONNECTION_ID,
        call_id=CALL_ID,
        attempt_id=ATTEMPT_ID,
        direction=CallDirection.INBOUND,
    )

    await gateway.inject_incoming(call, from_e164="+4915112345678")
    await gateway.answer(call)
    await gateway.speak(SpeakRequest(call=call, text="Guten Tag"))
    await gateway.stop_speaking(call)
    await gateway.hangup(call)

    events = gateway.drain_events()
    assert [event.kind for event in events] == [
        EventKind.INCOMING,
        EventKind.CONNECTED,
        EventKind.PLAYBACK_STARTED,
        EventKind.PLAYBACK_STOPPED,
        EventKind.DISCONNECTED,
    ]
    assert [event.sequence for event in events] == [1, 2, 3, 4, 5]
    assert all(event.call == call for event in events)


@pytest.mark.asyncio
async def test_foreign_project_reference_cannot_control_a_call() -> None:
    gateway = FakeTelephonyGateway()
    await gateway.register(connection_spec())
    call = outbound_call()
    await gateway.dial(DialRequest(call=call, to_e164="+49301234567"))
    foreign = call.model_copy(update={"project_id": OTHER_PROJECT_ID})

    with pytest.raises(GatewayError, match="call_not_found"):
        await gateway.hangup(foreign)

    assert gateway.active_calls == (call,)


@pytest.mark.parametrize("kind", [EventKind.SPEECH_PARTIAL, EventKind.SPEECH_FINAL])
def test_speech_events_require_a_transcript(kind: EventKind) -> None:
    with pytest.raises(ValidationError):
        GatewayEvent(
            kind=kind,
            call=outbound_call(),
            sequence=1,
            occurred_at=datetime.now(UTC),
        )


def test_event_requires_timezone_aware_timestamp() -> None:
    with pytest.raises(ValidationError):
        GatewayEvent(
            kind=EventKind.RINGING,
            call=outbound_call(),
            sequence=1,
            occurred_at=datetime.fromisoformat("2026-09-15T12:00:00"),
        )


def test_event_requires_utc_timestamp() -> None:
    with pytest.raises(ValidationError):
        GatewayEvent(
            kind=EventKind.RINGING,
            call=outbound_call(),
            sequence=1,
            occurred_at=datetime(2026, 9, 15, 12, tzinfo=timezone(timedelta(hours=2))),
        )
