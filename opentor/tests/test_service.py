from __future__ import annotations

import sqlite3
from contextlib import contextmanager

import pytest

pytest.importorskip("hydrahive")

from backend.models import FetchRequest, SearchRequest
from backend.policy import PolicyError
from backend.service import OpenTorService


class FakeAdapter:
    def status(self):
        return {"tor_reachable": True, "worker_ready": True, "last_error": None}

    def search(self, query, engines, limit, mode):
        return {"results": [{"title": "Observed result", "url": "https://example.org/a", "engine": "Ahmia", "confidence": 0.8}], "engines_used": ["Ahmia"], "total_raw": 1}

    def fetch(self, url):
        return {"url": url, "status": 200, "title": "Observed", "text": "Contact a.person@example.org", "links": [], "truncated": False}

    @staticmethod
    def extract_iocs(text):
        return {"emails": ["a.person@example.org"], "ips": ["203.0.113.10"]}


def test_policy_disabled_by_default(monkeypatch):
    service = OpenTorService(FakeAdapter())
    monkeypatch.setattr("backend.service.db", _db_context)
    assert service.policy()["enabled"] is False
    with pytest.raises(PolicyError, match="opentor_disabled"):
        import asyncio
        asyncio.run(service.search("user-1", None, SearchRequest(query="test")))


def test_fetch_marks_content_untrusted(monkeypatch):
    service = OpenTorService(FakeAdapter())
    monkeypatch.setattr("backend.service.db", _db_context)
    service.set_policy(__import__("backend.models", fromlist=["PolicyUpdate"]).PolicyUpdate(enabled=True))
    import asyncio
    result = asyncio.run(service.fetch("user-1", None, FetchRequest(url="https://example.org")))
    assert result["content_boundary"] == "UNTRUSTED_DATA"
    assert "a.person@example.org" not in result["data"]["text"]


_TEST_DB = sqlite3.connect(":memory:")
_TEST_DB.row_factory = sqlite3.Row
_TEST_DB.executescript("""
CREATE TABLE module_opentor_config (key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at TEXT);
CREATE TABLE module_opentor_evidence (id INTEGER PRIMARY KEY, owner_id TEXT, project_id TEXT, kind TEXT, source_url TEXT, payload_json TEXT, created_at TEXT);
INSERT INTO module_opentor_config VALUES ('enabled','0',CURRENT_TIMESTAMP);
INSERT INTO module_opentor_config VALUES ('max_chars','8000',CURRENT_TIMESTAMP);
INSERT INTO module_opentor_config VALUES ('retention_days','30',CURRENT_TIMESTAMP);
INSERT INTO module_opentor_config VALUES ('allowed_modes','["threat_intel","ransomware","corporate"]',CURRENT_TIMESTAMP);
""")


@contextmanager
def _db_context(immediate=False):
    if immediate:
        _TEST_DB.execute("BEGIN IMMEDIATE")
    try:
        yield _TEST_DB
        _TEST_DB.commit()
    except Exception:
        _TEST_DB.rollback()
        raise
