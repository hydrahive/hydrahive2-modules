from __future__ import annotations

import secrets
import time
from dataclasses import dataclass, replace
from threading import Lock

from .config import RESULT_TTL_SECONDS
from .models import ProfileDecision
from .result_selection import mark_challenge, unlock


@dataclass(frozen=True)
class StoredResult:
    owner: str
    decision: ProfileDecision
    expires_at: float
    claim_id: str | None = None
    claim_expires_at: float | None = None
    selection_session_id: str | None = None


class ResultStoreFull(RuntimeError):
    pass


class ResultStore:
    """TTL-Store mit benutzergetrennter Kapazität und atomarer Claim-Semantik."""

    def __init__(
        self,
        *,
        ttl_seconds: int = RESULT_TTL_SECONDS,
        max_entries: int = 250,
        claim_ttl_seconds: int | None = None,
    ) -> None:
        self._ttl = ttl_seconds
        self._claim_ttl = claim_ttl_seconds or ttl_seconds
        self._max_entries_per_owner = max_entries
        self._items: dict[str, StoredResult] = {}
        self._lock = Lock()

    def _refresh_expiry(
        self, result_id: str, item: StoredResult, now: float
    ) -> StoredResult | None:
        if (
            item.claim_id is not None
            and item.claim_expires_at is not None
            and item.claim_expires_at <= now
        ):
            if item.expires_at <= now:
                self._items.pop(result_id, None)
                return None
            item = replace(item, claim_id=None, claim_expires_at=None)
            self._items[result_id] = item
        elif item.claim_id is None and item.expires_at <= now:
            self._items.pop(result_id, None)
            return None
        return item

    def _cleanup(self, now: float) -> None:
        for result_id, item in list(self._items.items()):
            self._refresh_expiry(result_id, item, now)

    def _make_room(self, owner: str) -> None:
        owned = [
            (key, item) for key, item in self._items.items() if item.owner == owner
        ]
        while len(owned) >= self._max_entries_per_owner:
            available = [pair for pair in owned if pair[1].claim_id is None]
            if not available:
                raise ResultStoreFull("result_store_owner_capacity")
            oldest_key, _ = min(available, key=lambda pair: pair[1].expires_at)
            self._items.pop(oldest_key, None)
            owned = [pair for pair in owned if pair[0] != oldest_key]

    def put(self, owner: str, decision: ProfileDecision, *, now: float | None = None) -> str:
        timestamp = time.monotonic() if now is None else now
        with self._lock:
            self._cleanup(timestamp)
            self._make_room(owner)
            result_id = secrets.token_urlsafe(24)
            while result_id in self._items:
                result_id = secrets.token_urlsafe(24)
            self._items[result_id] = StoredResult(owner, decision, timestamp + self._ttl)
            return result_id

    def _owned(self, owner: str, result_id: str, now: float) -> StoredResult | None:
        item = self._items.get(result_id)
        if item is None:
            return None
        item = self._refresh_expiry(result_id, item, now)
        if item is None:
            return None
        return item if secrets.compare_digest(item.owner, owner) else None

    def get(self, owner: str, result_id: str, *, now: float | None = None) -> StoredResult | None:
        timestamp = time.monotonic() if now is None else now
        with self._lock:
            return self._owned(owner, result_id, timestamp)

    def claim(self, owner: str, result_id: str, *, now: float | None = None) -> StoredResult | None:
        timestamp = time.monotonic() if now is None else now
        with self._lock:
            item = self._owned(owner, result_id, timestamp)
            if item is None or item.claim_id is not None:
                return None
            claimed = replace(
                item,
                claim_id=secrets.token_urlsafe(24),
                claim_expires_at=timestamp + self._claim_ttl,
            )
            self._items[result_id] = claimed
            return claimed

    def mark_selection_challenge(
        self, owner: str, result_id: str, session_id: str,
        *, now: float | None = None,
    ) -> StoredResult | None:
        return mark_challenge(self, owner, result_id, session_id, now)

    def unlock_selection(
        self, owner: str, result_id: str, preference: str,
        *, session_id: str | None = None, now: float | None = None,
    ) -> StoredResult | None:
        return unlock(self, owner, result_id, preference, session_id, now)

    def renew(
        self, owner: str, result_id: str, claim_id: str, *, now: float | None = None
    ) -> bool:
        timestamp = time.monotonic() if now is None else now
        with self._lock:
            item = self._owned(owner, result_id, timestamp)
            if item is None or item.claim_id is None:
                return False
            if not secrets.compare_digest(item.claim_id, claim_id):
                return False
            self._items[result_id] = replace(
                item, claim_expires_at=timestamp + self._claim_ttl
            )
            return True

    def release(
        self, owner: str, result_id: str, claim_id: str, *, now: float | None = None
    ) -> bool:
        timestamp = time.monotonic() if now is None else now
        with self._lock:
            item = self._owned(owner, result_id, timestamp)
            if item is None or item.claim_id is None:
                return False
            if not secrets.compare_digest(item.claim_id, claim_id):
                return False
            if item.expires_at <= timestamp:
                self._items.pop(result_id, None)
            else:
                self._items[result_id] = replace(
                    item, claim_id=None, claim_expires_at=None
                )
            return True

    def consume(
        self, owner: str, result_id: str, claim_id: str, *, now: float | None = None
    ) -> ProfileDecision | None:
        timestamp = time.monotonic() if now is None else now
        with self._lock:
            item = self._owned(owner, result_id, timestamp)
            if item is None or item.claim_id is None:
                return None
            if not secrets.compare_digest(item.claim_id, claim_id):
                return None
            self._items.pop(result_id, None)
            return item.decision

    def clear(self) -> None:
        with self._lock:
            self._items.clear()


RESULTS = ResultStore()
