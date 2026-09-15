"""Asynchroner Port zwischen HydraHive und einem isolierten Telefonie-Gateway."""
from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol, runtime_checkable

from .models import (
    CallRef,
    ConnectionProbe,
    ConnectionRef,
    ConnectionSpec,
    DialRequest,
    GatewayEvent,
    GatewayHealth,
    SpeakRequest,
)


class GatewayError(RuntimeError):
    """Redaktionssicherer Fachfehler ohne Provider- oder Credential-Details."""

    def __init__(self, code: str, *, retryable: bool = False) -> None:
        self.code = code
        self.retryable = retryable
        super().__init__(code)


@runtime_checkable
class TelephonyGateway(Protocol):
    async def health(self) -> GatewayHealth: ...
    async def probe(self, connection: ConnectionSpec) -> ConnectionProbe: ...
    async def register(self, connection: ConnectionSpec) -> ConnectionRef: ...
    async def pause(self, connection: ConnectionRef) -> None: ...
    async def dial(self, request: DialRequest) -> CallRef: ...
    async def answer(self, call: CallRef) -> None: ...
    async def reject(self, call: CallRef, *, reason: str) -> None: ...
    async def hangup(self, call: CallRef) -> None: ...
    async def speak(self, request: SpeakRequest) -> None: ...
    async def stop_speaking(self, call: CallRef) -> None: ...
    def events(self) -> AsyncIterator[GatewayEvent]: ...
