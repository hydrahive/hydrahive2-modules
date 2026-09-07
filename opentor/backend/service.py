from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from hydrahive.db.connection import db

from .adapter import OpenTorAdapter
from .models import FetchRequest, PolicyUpdate, SearchRequest
from .policy import (
    PolicyError,
    RateLimiter,
    json_value,
    redact_text,
    untrusted_payload,
    validate_engines,
    validate_fetch_url,
    validate_redirect,
)


class OpenTorService:
    def __init__(self, adapter: OpenTorAdapter | None = None) -> None:
        self.adapter = adapter or OpenTorAdapter()
        self.limiter = RateLimiter()

    def policy(self) -> dict:
        with db() as conn:
            rows = conn.execute(
                "SELECT key, value FROM module_opentor_config"
            ).fetchall()
        values = {row["key"]: row["value"] for row in rows}
        return {
            "enabled": values.get("enabled") == "1",
            "max_chars": int(values.get("max_chars", "8000")),
            "retention_days": int(values.get("retention_days", "30")),
            "allowed_modes": json_value(values.get("allowed_modes"), ["threat_intel"]),
        }

    def set_policy(self, update: PolicyUpdate) -> dict:
        values = {
            "enabled": "1" if update.enabled else "0",
            "max_chars": str(update.max_chars),
            "retention_days": str(update.retention_days),
            "allowed_modes": json.dumps(update.allowed_modes),
        }
        with db(immediate=True) as conn:
            for key, value in values.items():
                conn.execute(
                    "INSERT INTO module_opentor_config(key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=CURRENT_TIMESTAMP",
                    (key, value),
                )
        return self.policy()

    def _check_enabled(self, owner_id: str, action: str) -> dict:
        policy = self.policy()
        if not policy["enabled"]:
            raise PolicyError("opentor_disabled")
        self.limiter.check(owner_id, action)
        return policy

    def status(self) -> dict:
        policy = self.policy()
        if not policy["enabled"]:
            return {"enabled": False, "worker_ready": False, "tor_reachable": False}
        try:
            status = self.adapter.status()
        except Exception:
            status = {"worker_ready": False, "tor_reachable": False, "last_error": "opentor_unavailable"}
        return {"enabled": True, **status}

    async def search(self, owner_id: str, project_id: str | None, request: SearchRequest) -> dict:
        import asyncio

        policy = self._check_enabled(owner_id, "search")
        if request.mode not in policy["allowed_modes"]:
            raise PolicyError("mode_not_allowed")
        validate_engines(request.engines)
        result = await asyncio.to_thread(
            self.adapter.search, request.query, request.engines, request.limit, request.mode,
        )
        safe_results = []
        for item in result.get("results", [])[: request.limit]:
            safe_results.append({
                "title": redact_text(str(item.get("title", "")), 300),
                "url": validate_fetch_url(str(item.get("url", ""))),
                "engine": str(item.get("engine", "unknown"))[:80],
                "confidence": item.get("confidence"),
            })
        payload = {
            "query": request.query,
            "mode": request.mode,
            "engines_used": result.get("engines_used", []),
            "total_raw": result.get("total_raw", len(safe_results)),
            "results": safe_results,
            "observed_at": datetime.now(timezone.utc).isoformat(),
        }
        self._save_evidence(owner_id, project_id, "search", None, payload, policy["retention_days"])
        return untrusted_payload(payload)

    async def fetch(self, owner_id: str, project_id: str | None, request: FetchRequest) -> dict:
        import asyncio

        policy = self._check_enabled(owner_id, "fetch")
        url = validate_fetch_url(request.url)
        result = await asyncio.to_thread(self.adapter.fetch, url)
        final_url = str(result.get("url") or url)
        validate_fetch_url(final_url)
        validate_redirect(url, final_url)
        max_chars = request.max_chars or policy["max_chars"]
        text = redact_text(str(result.get("text", "")), max_chars)
        safe_links = []
        for link in result.get("links", [])[:80]:
            if not isinstance(link, dict) or not link.get("href"):
                continue
            try:
                safe_links.append({
                    "text": redact_text(str(link.get("text", "")), 200),
                    "href": validate_fetch_url(str(link["href"])),
                })
            except PolicyError:
                continue
        payload = {
            "url": final_url,
            "status": int(result.get("status", 0)),
            "title": redact_text(str(result.get("title") or ""), 300),
            "text": text,
            "links": safe_links,
            "truncated": bool(result.get("truncated")),
            "error": "fetch_failed" if result.get("error") else None,
            "observed_at": datetime.now(timezone.utc).isoformat(),
        }
        self._save_evidence(owner_id, project_id, "fetch", final_url, payload, policy["retention_days"])
        return untrusted_payload(payload, source_url=final_url)

    def extract_iocs(self, owner_id: str, text: str) -> dict:
        self._check_enabled(owner_id, "extract_iocs")
        result = self.adapter.extract_iocs(text)
        # E-mail addresses and phone numbers are not returned verbatim.
        result["emails"] = ["[redacted-email]"] * min(len(result.get("emails", [])), 20)
        result["phones"] = ["[redacted-phone]"] * min(len(result.get("phones", [])), 20)
        return {"content_boundary": "UNTRUSTED_DATA", "iocs": result}

    @staticmethod
    def _save_evidence(
        owner_id: str,
        project_id: str | None,
        kind: str,
        source_url: str | None,
        payload: dict,
        retention_days: int,
    ) -> None:
        with db() as conn:
            conn.execute(
                "DELETE FROM module_opentor_evidence WHERE created_at < datetime('now', ?)",
                (f"-{retention_days} days",),
            )
            conn.execute(
                "INSERT INTO module_opentor_evidence(owner_id, project_id, kind, source_url, payload_json) VALUES (?, ?, ?, ?, ?)",
                (owner_id, project_id, kind, source_url, json.dumps(payload, ensure_ascii=False)),
            )
