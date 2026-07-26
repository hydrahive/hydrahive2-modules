from __future__ import annotations

from .errors import SabResponseError
from .sab_credentials import SabConnection
from .sabnzbd import _request_json


def _slots(payload: object, mode: str) -> list[dict]:
    if not isinstance(payload, dict):
        raise SabResponseError("sab_response_invalid")
    container = payload.get(mode)
    if not isinstance(container, dict) or not isinstance(container.get("slots"), list):
        raise SabResponseError("sab_response_invalid")
    slots = container["slots"]
    if len(slots) > 10_000 or not all(isinstance(item, dict) for item in slots):
        raise SabResponseError("sab_response_invalid")
    return slots


async def find_handoff(connection: SabConnection, marker: str) -> str | None:
    matches: set[str] = set()
    for mode in ("queue", "history"):
        payload = await _request_json(connection, mode)
        for item in _slots(payload, mode):
            names = [item.get(key) for key in ("filename", "name", "nzb_name")]
            if not any(isinstance(name, str) and marker in name for name in names):
                continue
            job_id = item.get("nzo_id")
            if not isinstance(job_id, str) or connection.api_key in job_id:
                raise SabResponseError("sab_response_invalid")
            matches.add(job_id)
    if len(matches) > 1:
        raise SabResponseError("sab_reconciliation_ambiguous")
    return next(iter(matches), None)
