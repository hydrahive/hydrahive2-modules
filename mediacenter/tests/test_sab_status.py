from __future__ import annotations

import pytest

from backend import sab_status
from backend.errors import SabResponseError
from backend.sab_credentials import SabConnection

_CONNECTION = SabConnection("https://sabnzb.home.server.ha", "secret-key")


async def test_fetch_status_only_projects_allowed_ids_and_sanitizes(monkeypatch):
    async def response(connection, mode):
        return {
            mode: {
                "slots": [
                    {
                        "nzo_id": "SABnzbd_nzo_owned",
                        "filename": "/secret/path/file.nzb",
                        "status": "Downloading",
                        "percentage": "125",
                        "timeleft": "00:12:34",
                        "error": "raw upstream secret /path",
                    },
                    {"nzo_id": "SABnzbd_nzo_foreign", "status": "Failed"},
                ]
            }
        }

    monkeypatch.setattr(sab_status, "_request_json", response)
    result = await sab_status.fetch_owned_status(
        _CONNECTION, "queue", {"SABnzbd_nzo_owned"}
    )
    assert result == {
        "SABnzbd_nzo_owned": {
            "status": "downloading",
            "progress": 100.0,
            "eta": "00:12:34",
            "error_code": None,
        }
    }
    assert "path" not in str(result)


async def test_handoff_reconciliation_batches_and_requires_exact_prefix(monkeypatch):
    calls = []

    async def response(connection, mode):
        calls.append(mode)
        return {mode: {"slots": [
            {"nzo_id": "SABnzbd_nzo_good", "filename": "hh-one Film"},
            {"nzo_id": "SABnzbd_nzo_bad", "filename": "prefix hh-two Film"},
        ]}}

    monkeypatch.setattr(sab_status, "_request_json", response)
    result = await sab_status.find_handoffs(_CONNECTION, {"hh-one", "hh-two"})
    assert result == {"hh-one": "SABnzbd_nzo_good"}
    assert calls == ["queue", "history"]


async def test_status_rejects_oversized_slot_list(monkeypatch):
    async def response(connection, mode):
        return {mode: {"slots": [{}] * 10_001}}

    monkeypatch.setattr(sab_status, "_request_json", response)
    with pytest.raises(SabResponseError):
        await sab_status.fetch_owned_status(_CONNECTION, "history", set())
