"""Eingabe-Schemas der Routen. Grobe Prüfung hier (Typen, keine Extra-Felder); die genauen Regeln in accounts.py."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt

Tls = Literal["ssl", "starttls"]
Port = Literal[993, 143, 465, 587, 25]


class AccountIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: str = Field(min_length=1, max_length=200)
    address: str = Field(min_length=3, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    sender_name: str = Field(default="", max_length=200)
    imap_host: str = Field(min_length=1, max_length=253)
    imap_port: Port = 993
    imap_tls: Tls = "ssl"
    smtp_host: str = Field(default="", max_length=253)
    smtp_port: Port = 465
    smtp_tls: Tls = "ssl"
    username: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=1, max_length=500)


class AccountPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: str | None = Field(default=None, min_length=1, max_length=200)
    sender_name: str | None = Field(default=None, max_length=200)
    imap_host: str | None = Field(default=None, min_length=1, max_length=253)
    imap_port: Port | None = None
    imap_tls: Tls | None = None
    smtp_host: str | None = Field(default=None, max_length=253)
    smtp_port: Port | None = None
    smtp_tls: Tls | None = None
    username: str | None = Field(default=None, min_length=1, max_length=200)
    signature: str | None = Field(default=None, max_length=5000)
    password: str | None = Field(default=None, min_length=1, max_length=500)


class Paging(BaseModel):
    limit: StrictInt = 50
    offset: StrictInt = 0
