"""L3: Anmeldung an der Durchreiche. Platzhalter."""
from __future__ import annotations

import time  # noqa: F401

_tickets: dict = {}


def _key() -> bytes:
    raise NotImplementedError
