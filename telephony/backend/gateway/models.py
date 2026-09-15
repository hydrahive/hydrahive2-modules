"""Strikte Fachmodelle des transportneutralen Telefonie-Gatewayvertrags."""
from __future__ import annotations

from datetime import datetime, timedelta
from enum import StrEnum
from uuid import UUID

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    field_validator,
    model_validator,
)


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class TransportKind(StrEnum):
    UDP = "udp"
    TCP = "tcp"
    TLS = "tls"


class CallDirection(StrEnum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class EventKind(StrEnum):
    INCOMING = "incoming"
    DIALING = "dialing"
    RINGING = "ringing"
    CONNECTED = "connected"
    SPEECH_PARTIAL = "speech.partial"
    SPEECH_FINAL = "speech.final"
    PLAYBACK_STARTED = "playback.started"
    PLAYBACK_STOPPED = "playback.stopped"
    DTMF = "dtmf"
    VOICEMAIL_DETECTED = "voicemail.detected"
    BUSY = "busy"
    NO_ANSWER = "no_answer"
    REJECTED = "rejected"
    FAILED = "failed"
    DISCONNECTED = "disconnected"


class ConnectionRef(ContractModel):
    project_id: UUID
    connection_id: UUID


class ConnectionSpec(ConnectionRef):
    """Flüchtige Gateway-Konfiguration; Benutzername und Passwort bleiben maskiert."""

    registrar: str = Field(min_length=1, max_length=253)
    port: int = Field(default=5060, ge=1, le=65535)
    transport: TransportKind = TransportKind.UDP
    username: SecretStr
    password: SecretStr

    @field_validator("registrar")
    @classmethod
    def validate_registrar(cls, value: str) -> str:
        host = value.strip()
        if not host or "://" in host or "/" in host or any(char.isspace() for char in host):
            raise ValueError("registrar must be a host without scheme, path or whitespace")
        return host

    @field_validator("username", "password")
    @classmethod
    def reject_empty_secret(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value():
            raise ValueError("credential must not be empty")
        return value


class CallRef(ConnectionRef):
    call_id: UUID
    attempt_id: UUID
    direction: CallDirection


class DialRequest(ContractModel):
    call: CallRef
    to_e164: str = Field(pattern=r"^\+[1-9][0-9]{6,14}$")

    @model_validator(mode="after")
    def require_outbound_call(self) -> DialRequest:
        if self.call.direction is not CallDirection.OUTBOUND:
            raise ValueError("dial requires an outbound call reference")
        return self


class SpeakRequest(ContractModel):
    call: CallRef
    text: str = Field(min_length=1, max_length=2000)


class GatewayHealth(ContractModel):
    ready: bool
    implementation: str = Field(min_length=1, max_length=80)
    version: str = Field(min_length=1, max_length=40)
    live_telephony_verified: bool
    observed_at: AwareDatetime

    @field_validator("observed_at")
    @classmethod
    def require_utc(cls, value: datetime) -> datetime:
        if value.utcoffset() != timedelta(0):
            raise ValueError("observed_at must use UTC")
        return value


class ConnectionProbe(ContractModel):
    reachable: bool
    authenticated: bool
    detail_code: str = Field(min_length=1, max_length=80)


class GatewayEvent(ContractModel):
    kind: EventKind
    call: CallRef
    sequence: int = Field(ge=1)
    occurred_at: AwareDatetime
    remote_e164: str | None = Field(default=None, pattern=r"^\+[1-9][0-9]{6,14}$", repr=False)
    transcript: str | None = Field(default=None, min_length=1, max_length=8000, repr=False)
    confidence: float | None = Field(default=None, ge=0, le=1, repr=False)
    digit: str | None = Field(default=None, pattern=r"^[0-9A-D*#]$")
    reason: str | None = Field(default=None, min_length=1, max_length=80)

    @field_validator("occurred_at")
    @classmethod
    def require_utc(cls, value: datetime) -> datetime:
        if value.utcoffset() != timedelta(0):
            raise ValueError("occurred_at must use UTC")
        return value

    @model_validator(mode="after")
    def validate_payload_for_kind(self) -> GatewayEvent:
        speech = self.kind in {EventKind.SPEECH_PARTIAL, EventKind.SPEECH_FINAL}
        if speech != (self.transcript is not None):
            raise ValueError("transcript is required only for speech events")
        if self.kind is EventKind.DTMF and self.digit is None:
            raise ValueError("digit is required for dtmf events")
        if self.kind is not EventKind.DTMF and self.digit is not None:
            raise ValueError("digit is only valid for dtmf events")
        if self.kind is EventKind.INCOMING and self.remote_e164 is None:
            raise ValueError("remote_e164 is required for incoming events")
        if self.kind is EventKind.FAILED and self.reason is None:
            raise ValueError("reason is required for failed events")
        return self


def utc_now() -> datetime:
    """Kleine injizierbare Uhr für Gateway-Implementierungen und Tests."""
    from datetime import UTC

    return datetime.now(UTC)
