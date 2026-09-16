"""Strict API models for the ephemeral FRITZ!Box registration probe."""

from __future__ import annotations

import ipaddress
import os
import re
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator

_RFC1918_NETWORKS = tuple(
    ipaddress.ip_network(network)
    for network in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")
)
_USERNAME_PATTERN = re.compile(r"[A-Za-z0-9._-]{8,64}\Z")
_PASSWORD_PATTERN = re.compile(r"[A-Za-z0-9._!$%&()*+,\-/:<=>?@^`{|}~]{12,128}\Z")
SPIKE_REGISTRAR = os.environ.get("HH_TELEPHONY_SPIKE_REGISTRAR", "192.168.3.1")
try:
    SPIKE_PORT = int(os.environ.get("HH_TELEPHONY_SPIKE_PORT", "5060"))
    _configured_address = ipaddress.ip_address(SPIKE_REGISTRAR)
except ValueError as exc:
    raise RuntimeError("invalid telephony spike target configuration") from exc
if (
    _configured_address.version != 4
    or not any(_configured_address in network for network in _RFC1918_NETWORKS)
    or not 1 <= SPIKE_PORT <= 65535
):
    raise RuntimeError("invalid telephony spike target configuration")


class ProbeOutcome(StrEnum):
    REGISTERED = "registered"
    AUTH_FAILED = "auth_failed"
    REGISTRATION_FAILED = "registration_failed"
    TIMEOUT = "timeout"
    RUNTIME_UNAVAILABLE = "runtime_unavailable"
    BUSY = "busy"


class RegistrationProbeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)

    registrar: str = Field(min_length=7, max_length=15)
    port: int = Field(ge=1, le=65535, strict=True)
    username: str = Field(min_length=8, max_length=64, repr=False)
    password: SecretStr = Field(min_length=12, max_length=128, repr=False)

    @model_validator(mode="after")
    def validate_sip_values(self) -> RegistrationProbeRequest:
        try:
            address = ipaddress.ip_address(self.registrar)
        except ValueError as exc:
            raise ValueError("registrar must be private IPv4") from exc
        if address.version != 4 or not any(
            address in network for network in _RFC1918_NETWORKS
        ):
            raise ValueError("registrar must be private IPv4")
        if self.registrar != SPIKE_REGISTRAR or self.port != SPIKE_PORT:
            raise ValueError("registrar is not allowlisted")
        if not _USERNAME_PATTERN.fullmatch(self.username):
            raise ValueError("username contains unsupported characters")
        if not _PASSWORD_PATTERN.fullmatch(self.password.get_secret_value()):
            raise ValueError("password contains unsupported characters")
        return self


class RegistrationProbeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    outcome: ProbeOutcome
