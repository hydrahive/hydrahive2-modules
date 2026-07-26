from __future__ import annotations

import re

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


async def find_handoffs(
    connection: SabConnection, markers: set[str]
) -> dict[str, str]:
    matches: dict[str, set[str]] = {marker: set() for marker in markers}
    for mode in ("queue", "history"):
        payload = await _request_json(connection, mode)
        for item in _slots(payload, mode):
            names = [item.get(key) for key in ("filename", "name", "nzb_name")]
            matched = {
                marker for marker in markers
                if any(isinstance(name, str) and name.startswith(f"{marker} ") for name in names)
            }
            if not matched:
                continue
            job_id = item.get("nzo_id")
            if (
                not isinstance(job_id, str)
                or connection.api_key in job_id
                or not re.fullmatch(r"SABnzbd_nzo_[A-Za-z0-9_-]{1,128}", job_id)
            ):
                raise SabResponseError("sab_response_invalid")
            for marker in matched:
                matches[marker].add(job_id)
    if any(len(job_ids) > 1 for job_ids in matches.values()):
        raise SabResponseError("sab_reconciliation_ambiguous")
    return {
        marker: next(iter(job_ids)) for marker, job_ids in matches.items() if job_ids
    }


async def find_handoff(connection: SabConnection, marker: str) -> str | None:
    return (await find_handoffs(connection, {marker})).get(marker)


def _progress(value: object) -> float | None:
    try:
        number = float(str(value).rstrip("%"))
    except (TypeError, ValueError):
        return None
    return max(0.0, min(number, 100.0))


async def fetch_owned_status(
    connection: SabConnection, mode: str, allowed_ids: set[str]
) -> dict[str, dict]:
    if mode not in {"queue", "history"}:
        raise ValueError("invalid_mode")
    payload = await _request_json(connection, mode)
    result: dict[str, dict] = {}
    for item in _slots(payload, mode):
        job_id = item.get("nzo_id")
        if not isinstance(job_id, str) or job_id not in allowed_ids:
            continue
        raw_status = str(item.get("status", "")).lower()
        status = raw_status if raw_status in {
            "queued", "downloading", "paused", "extracting", "completed", "failed"
        } else "unknown"
        eta_value = item.get("timeleft")
        eta = eta_value if isinstance(eta_value, str) and re.fullmatch(
            r"[0-9: .-]{1,32}", eta_value
        ) else None
        result[job_id] = {
            "status": status,
            "progress": _progress(item.get("percentage")),
            "eta": eta,
            "error_code": "sab_job_failed" if status == "failed" else None,
        }
    return result
