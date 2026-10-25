"""Eingaben der SIP-Verbindung (PLAN-EINSTELLUNGEN „Felder“).

Nur was nachweislich gebraucht wird; jede Angabe begrenzt, weil sie in SIP-Kopfzeilen landet (keine Zeilenumbrüche).
Das Kennwort ist ein SecretStr und erscheint nie in repr() oder model_dump().
"""
from __future__ import annotations

import re
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    field_validator,
    model_validator,
)

PBX = Literal["fritzbox", "sip"]
_HOST_RE = re.compile(r"^(?=.{1,253}$)[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?(\.[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)*$")
_USER_RE = re.compile(r"^[A-Za-z0-9._!~*'()+=$,;?/&%-]{1,128}$")
_NUMBER_RE = re.compile(r"^\+?[0-9 ()/-]{3,30}$")
_RTP_MAX_SPAN = 400


class ConnectionIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    pbx: PBX = "fritzbox"
    display_name: str = Field("HydraHive", max_length=80)
    registrar: str = Field(min_length=1, max_length=253)
    registrar_port: int = Field(5060, ge=1, le=65535)
    username: str = Field(min_length=1, max_length=128)
    password: SecretStr | None = Field(None, max_length=128)
    own_number: str = Field("", max_length=30)
    local_sip_port: int = Field(5070, ge=1024, le=65535)
    rtp_port_min: int = Field(7078, ge=1024, le=65534)
    rtp_port_max: int = Field(7109, ge=1025, le=65535)
    register_interval: int = Field(300, ge=60, le=3600)

    @field_validator("display_name")
    @classmethod
    def _name(cls, v: str) -> str:
        if any(ch in v for ch in '\r\n"<>\\') or any(ord(ch) < 32 for ch in v):
            raise ValueError("Anzeigename enthält unerlaubte Zeichen")
        return v or "HydraHive"

    @field_validator("registrar")
    @classmethod
    def _host(cls, v: str) -> str:
        v = v.lower().rstrip(".")
        if not _HOST_RE.match(v):
            raise ValueError("Adresse ungültig (Name oder IP, ohne http:// und Port)")
        return v

    @field_validator("username")
    @classmethod
    def _user(cls, v: str) -> str:
        if not _USER_RE.match(v):
            raise ValueError("Benutzername enthält unerlaubte Zeichen")
        return v

    @field_validator("own_number")
    @classmethod
    def _number(cls, v: str) -> str:
        if v and not _NUMBER_RE.match(v):
            raise ValueError("Rufnummer: nur Ziffern, Leerzeichen, + ( ) / -")
        return v

    @model_validator(mode="after")
    def _together(self) -> ConnectionIn:
        if self.password is not None and not self.password.get_secret_value():
            self.password = None                          # leer = beim Ändern unverändert lassen
        if self.rtp_port_min % 2:
            raise ValueError("Sprach-Ports: Beginn muss eine gerade Zahl sein")
        if self.rtp_port_max <= self.rtp_port_min:
            raise ValueError("Sprach-Ports: Ende muss größer als Beginn sein")
        if self.rtp_port_max - self.rtp_port_min > _RTP_MAX_SPAN:
            raise ValueError(f"Sprach-Ports: höchstens {_RTP_MAX_SPAN} Ports")
        if self.rtp_port_min <= self.local_sip_port <= self.rtp_port_max:
            raise ValueError("Lokaler SIP-Port darf nicht im Bereich der Sprach-Ports liegen")
        if self.pbx == "fritzbox":
            if len(self.username) < 8:
                raise ValueError("FRITZ!Box: Benutzername mindestens 8 Zeichen")
            if self.password is not None and len(self.password.get_secret_value()) < 8:
                raise ValueError("FRITZ!Box: Kennwort mindestens 8 Zeichen")
        return self

    def public(self) -> dict:
        """Alle Felder außer dem Kennwort."""
        return self.model_dump(exclude={"password"})
