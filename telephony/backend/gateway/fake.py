"""Deterministischer In-Process-Fake für Gateway-Contract- und Service-Tests."""
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from .models import (
    CallDirection,
    CallRef,
    ConnectionProbe,
    ConnectionRef,
    ConnectionSpec,
    DialRequest,
    EventKind,
    GatewayEvent,
    GatewayHealth,
    SpeakRequest,
    utc_now,
)
from .protocol import GatewayError


@dataclass(slots=True)
class _CallRecord:
    call: CallRef
    state: str
    playing: bool = False


class FakeTelephonyGateway:
    """Stateful fake with no sockets, persistence, credentials or telephony claims."""

    def __init__(
        self,
        *,
        probe_reachable: bool = True,
        probe_authenticated: bool = True,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self._probe_reachable = probe_reachable
        self._probe_authenticated = probe_authenticated
        self._clock = clock
        self._registered: set[ConnectionRef] = set()
        self._calls: dict[UUID, _CallRecord] = {}
        self._attempts: dict[UUID, DialRequest | CallRef] = {}
        self._sequences: dict[UUID, int] = {}
        self._events: asyncio.Queue[GatewayEvent] = asyncio.Queue()

    @property
    def registered_connections(self) -> tuple[ConnectionRef, ...]:
        return tuple(sorted(self._registered, key=lambda ref: str(ref.connection_id)))

    @property
    def active_calls(self) -> tuple[CallRef, ...]:
        active = [record.call for record in self._calls.values() if record.state != "terminal"]
        return tuple(sorted(active, key=lambda call: str(call.call_id)))

    async def health(self) -> GatewayHealth:
        return GatewayHealth(
            ready=True,
            implementation="fake",
            version="1",
            live_telephony_verified=False,
            observed_at=self._clock(),
        )

    async def probe(self, connection: ConnectionSpec) -> ConnectionProbe:
        del connection  # Credentials are validated, then deliberately not retained.
        authenticated = self._probe_reachable and self._probe_authenticated
        detail = "ok" if authenticated else "unreachable" if not self._probe_reachable else "auth_failed"
        return ConnectionProbe(
            reachable=self._probe_reachable,
            authenticated=authenticated,
            detail_code=detail,
        )

    async def register(self, connection: ConnectionSpec) -> ConnectionRef:
        ref = self._connection_ref(connection)
        self._registered.add(ref)
        return ref

    async def pause(self, connection: ConnectionRef) -> None:
        self._registered.discard(connection)

    async def dial(self, request: DialRequest) -> CallRef:
        self._require_registered(request.call)
        previous = self._attempts.get(request.call.attempt_id)
        if previous is not None:
            if previous == request:
                return request.call
            raise GatewayError("attempt_conflict")
        if request.call.call_id in self._calls:
            raise GatewayError("call_conflict")
        self._attempts[request.call.attempt_id] = request
        self._calls[request.call.call_id] = _CallRecord(request.call, "dialing")
        self._emit(EventKind.DIALING, request.call)
        return request.call

    async def inject_incoming(self, call: CallRef, *, from_e164: str) -> None:
        """Test-side input standing in for a sidecar's incoming-call event."""
        if call.direction is not CallDirection.INBOUND:
            raise GatewayError("invalid_call_direction")
        self._require_registered(call)
        if call.call_id in self._calls or call.attempt_id in self._attempts:
            raise GatewayError("call_conflict")
        self._attempts[call.attempt_id] = call
        self._calls[call.call_id] = _CallRecord(call, "incoming")
        self._emit(EventKind.INCOMING, call, remote_e164=from_e164)

    async def answer(self, call: CallRef) -> None:
        record = self._record(call)
        if record.state != "incoming":
            raise GatewayError("invalid_call_state")
        record.state = "connected"
        self._emit(EventKind.CONNECTED, call)

    async def reject(self, call: CallRef, *, reason: str) -> None:
        record = self._record(call)
        if record.state == "terminal":
            return
        if record.state != "incoming":
            raise GatewayError("invalid_call_state")
        record.state = "terminal"
        self._emit(EventKind.REJECTED, call, reason=reason)

    async def hangup(self, call: CallRef) -> None:
        record = self._record(call)
        if record.state == "terminal":
            return
        record.state = "terminal"
        record.playing = False
        self._emit(EventKind.DISCONNECTED, call, reason="local_hangup")

    async def speak(self, request: SpeakRequest) -> None:
        record = self._record(request.call)
        if record.state != "connected":
            raise GatewayError("invalid_call_state")
        if record.playing:
            raise GatewayError("playback_active")
        record.playing = True
        self._emit(EventKind.PLAYBACK_STARTED, request.call)

    async def stop_speaking(self, call: CallRef) -> None:
        record = self._record(call)
        if record.state != "connected":
            raise GatewayError("invalid_call_state")
        if not record.playing:
            return
        record.playing = False
        self._emit(EventKind.PLAYBACK_STOPPED, call)

    async def events(self) -> AsyncIterator[GatewayEvent]:
        while True:
            yield await self._events.get()

    def drain_events(self) -> list[GatewayEvent]:
        events: list[GatewayEvent] = []
        while not self._events.empty():
            events.append(self._events.get_nowait())
        return events

    def _require_registered(self, call: CallRef) -> None:
        if self._connection_ref(call) not in self._registered:
            raise GatewayError("connection_not_registered", retryable=True)

    def _record(self, call: CallRef) -> _CallRecord:
        record = self._calls.get(call.call_id)
        if record is None or record.call != call:
            raise GatewayError("call_not_found")
        return record

    def _emit(self, kind: EventKind, call: CallRef, **payload: object) -> None:
        sequence = self._sequences.get(call.call_id, 0) + 1
        event = GatewayEvent(
            kind=kind,
            call=call,
            sequence=sequence,
            occurred_at=self._clock(),
            **payload,
        )
        self._sequences[call.call_id] = sequence
        self._events.put_nowait(event)

    @staticmethod
    def _connection_ref(value: ConnectionRef) -> ConnectionRef:
        return ConnectionRef(project_id=value.project_id, connection_id=value.connection_id)
