from __future__ import annotations

from pydantic import BaseModel, Field

from .loyalty_models import ConnectionVisibility, LoyaltyProvider


class LoyaltyConnectionCreate(BaseModel):
    provider: LoyaltyProvider
    credential_ref: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{0,49}$")
    provider_account_id: str = Field(min_length=1, max_length=256)
    masked_account: str = Field(min_length=1, max_length=120)
    alias: str | None = Field(default=None, min_length=1, max_length=120)
    country_code: str = Field(default="DE", pattern=r"^[A-Z]{2}$")
    language_code: str = Field(default="de", pattern=r"^[a-z]{2}(?:-[A-Z]{2})?$")
    visibility: ConnectionVisibility = "owner"


class LoyaltyConnectionUpdate(BaseModel):
    alias: str | None = Field(default=None, min_length=1, max_length=120)
    visibility: ConnectionVisibility = "owner"
    revision: int = Field(ge=1)
