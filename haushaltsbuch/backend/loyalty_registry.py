"""Laufzeit-Registry für austauschbare Loyalty-Provider-Adapter."""
from __future__ import annotations

from .loyalty_models import LoyaltyProvider
from .loyalty_provider import LoyaltyProviderAdapter

_adapters: dict[LoyaltyProvider, LoyaltyProviderAdapter] = {}


def register(adapter: LoyaltyProviderAdapter) -> None:
    _adapters[adapter.provider_id] = adapter


def unregister(provider: LoyaltyProvider) -> None:
    _adapters.pop(provider, None)


def get(provider: LoyaltyProvider) -> LoyaltyProviderAdapter | None:
    return _adapters.get(provider)
