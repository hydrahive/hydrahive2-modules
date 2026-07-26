from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IndexerCapabilities:
    max_limit: int
    default_limit: int
    search_types: set[str]
    categories: set[int]
