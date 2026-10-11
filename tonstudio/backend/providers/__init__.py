"""Registry der Musik-Anbieter (SPEC.md §5.6). Neue Anbieter (z. B. ACE-Step lokal, M1b) kommen hier dazu."""
from __future__ import annotations

from ._base import MusicBackend, MusicModel, MusicResult, ProviderError
from .openrouter import OpenRouterBackend

__all__ = ["BACKENDS", "MusicModel", "MusicResult", "ProviderError", "UnknownModel", "list_models", "resolve"]

BACKENDS: list[MusicBackend] = [OpenRouterBackend()]


class UnknownModel(LookupError):
    pass


async def list_models() -> list[MusicModel]:
    out: list[MusicModel] = []
    for b in BACKENDS:
        out.extend(await b.list_models())
    return out


async def resolve(model_id: str) -> tuple[MusicModel, MusicBackend]:
    for b in BACKENDS:
        for m in await b.list_models():
            if m.id == model_id:
                return m, b
    raise UnknownModel(model_id)
