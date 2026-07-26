from __future__ import annotations

import re

_JOB_ID = re.compile(
    r"(?:SABnzbd_nzo_[A-Za-z0-9_-]{1,128}|"
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-"
    r"[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12})\Z"
)


def is_valid_job_id(value: object, secret: str) -> bool:
    return isinstance(value, str) and secret not in value and bool(_JOB_ID.fullmatch(value))
