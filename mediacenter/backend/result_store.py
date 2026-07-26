from __future__ import annotations

import secrets
import time
from dataclasses import dataclass
from threading import Lock

from .config import RESULT_TTL_SECONDS
from .models import ProfileDecision


@dataclass(frozen=True)
class StoredResult:
    owner: str
    decision: ProfileDecision
    expires_at: float


class ResultStore:
    def __init__(self, *, ttl_seconds: int = RESULT_TTL_SECONDS, max_entries: int = 5_000) -> None:
        self._ttl = ttl_seconds
        self._max_entries = max_entries
        self._items: dict[str, StoredResult] = {}
        self._lock = Lock()

    def _cleanup(self, now: float) -> None:
        expired = [key for key, value in self._items.items() if value.expires_at <= now]
        for key in expired:
            self._items.pop(key, None)
        while len(self._items) >= self._max_entries and self._items:
            oldest = min(self._items, key=lambda key: self._items[key].expires_at)
            self._items.pop(oldest, None)

    def put(self, owner: str, decision: ProfileDecision, *, now: float | None = None) -> str:
        timestamp = time.monotonic() if now is None else now
        with self._lock:
            self._cleanup(timestamp)
            result_id = secrets.token_urlsafe(24)
            while result_id in self._items:
                result_id = secrets.token_urlsafe(24)
            self._items[result_id] = StoredResult(owner, decision, timestamp + self._ttl)
            return result_id

    def get(self, owner: str, result_id: str, *, now: float | None = None) -> StoredResult | None:
        timestamp = time.monotonic() if now is None else now
        with self._lock:
            item = self._items.get(result_id)
            if item is None or item.expires_at <= timestamp:
                self._items.pop(result_id, None)
                return None
            return item if secrets.compare_digest(item.owner, owner) else None

    def clear(self) -> None:
        with self._lock:
            self._items.clear()


RESULTS = ResultStore()
