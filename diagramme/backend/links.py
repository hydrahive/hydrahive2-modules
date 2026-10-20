"""Signierte Ansichts-Adresse (Spec §4a): HMAC-SHA256, eigener Zweck-Schlüssel, 10 Minuten, zeitkonstanter Vergleich.

Der Rahmen im Chat kann keinen Anmelde-Kopf schicken, das Token soll nicht in die Adresse. Darum diese kurzlebige,
nur für ein Diagramm gültige Signatur.
"""
from __future__ import annotations

import hashlib
import hmac
import time

TTL_SECONDS = 600
_CONTEXT = b"hydrahive-modul-diagramme-ansicht-v1"
DEVICE_BASE = "/api/module-device/diagramme/sandbox"


def _key() -> bytes:
    from hydrahive.settings import settings
    return hmac.new(settings.secret_key.encode(), _CONTEXT, hashlib.sha256).digest()


def _mac(text: str) -> str:
    return hmac.new(_key(), text.encode(), hashlib.sha256).hexdigest()


def _payload(view_id: str, exp: int) -> str:
    return f"diagramme|view|{view_id}|{exp}"


def sign(view_id: str, *, now: float | None = None) -> tuple[int, str]:
    exp = int(now if now is not None else time.time()) + TTL_SECONDS
    return exp, _mac(_payload(view_id, exp))


def check(view_id: str, exp: int, sig: object, *, now: float | None = None) -> bool:
    current = int(now if now is not None else time.time())
    if not isinstance(sig, str) or not isinstance(exp, int):
        return False
    if exp <= current or exp > current + TTL_SECONDS:
        return False
    return hmac.compare_digest(_mac(_payload(view_id, exp)), sig)


def view_url(view_id: str, *, now: float | None = None) -> str:
    exp, sig = sign(view_id, now=now)
    return f"{DEVICE_BASE}/{view_id}?exp={exp}&sig={sig}"
