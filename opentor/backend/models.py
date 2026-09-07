from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

Mode = Literal["threat_intel", "ransomware", "corporate"]


class SearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=200)
    mode: Mode = "threat_intel"
    engines: list[str] = Field(default_factory=list, max_length=12)
    limit: int = Field(default=10, ge=1, le=20)

    @field_validator("query")
    @classmethod
    def query_not_blank(cls, value: str) -> str:
        value = " ".join(value.split())
        if not value:
            raise ValueError("query must not be blank")
        return value

    @field_validator("engines")
    @classmethod
    def engines_normalized(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(item.strip() for item in value if item.strip()))


class FetchRequest(BaseModel):
    url: str = Field(min_length=8, max_length=2048)
    max_chars: int | None = Field(default=None, ge=500, le=8000)


class ExtractRequest(BaseModel):
    text: str = Field(min_length=1, max_length=8000)


class PolicyUpdate(BaseModel):
    enabled: bool
    max_chars: int = Field(default=8000, ge=500, le=8000)
    retention_days: int = Field(default=30, ge=1, le=365)
    allowed_modes: list[Mode] = Field(default_factory=lambda: ["threat_intel", "ransomware", "corporate"])


class EvidenceEnvelope(BaseModel):
    source_url: str | None = None
    observed_at: str
    content_boundary: Literal["UNTRUSTED_DATA"] = "UNTRUSTED_DATA"
    labels: list[str]
    data: dict
