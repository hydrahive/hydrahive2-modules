"""L3: nginx-Block der Durchreiche. Platzhalter."""
from __future__ import annotations

import os  # noqa: F401
import subprocess  # noqa: F401


def nginx_conf(ip: str) -> str:
    raise NotImplementedError


def apply(ip, *, root, data_dir) -> bool:
    raise NotImplementedError


def remove(*, root, data_dir) -> None:
    raise NotImplementedError


def root(script: str):
    raise NotImplementedError
