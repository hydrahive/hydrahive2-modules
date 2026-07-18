"""Feste, reverse-engineerte Lidl-Clientparameter für den opt-in Testconnector."""
from __future__ import annotations

import base64
import os

AUTH_URL = "https://accounts.lidl.com/connect/authorize"
TOKEN_URL = "https://accounts.lidl.com/connect/token"
USERINFO_URL = "https://accounts.lidl.com/connect/userinfo"
TICKETS_V2_URL = "https://tickets.lidlplus.com/api/v2"
TICKETS_V3_URL = "https://tickets.lidlplus.com/api/v3"
CLIENT_ID = "LidlPlusNativeClient"
# Öffentlicher Wert des nativen Clients; kein installations- oder nutzerspezifisches Secret.
_NATIVE_PUBLIC_PASSWORD = "secret"
REDIRECT_URI = "com.lidlplus.app://callback"
SCOPE = "openid profile offline_access lpprofile lpapis"


def token_headers() -> dict[str, str]:
    value = base64.b64encode(
        f"{CLIENT_ID}:{_NATIVE_PUBLIC_PASSWORD}".encode()
    ).decode()
    return {
        "Authorization": f"Basic {value}",
        "Content-Type": "application/x-www-form-urlencoded",
    }


def enabled() -> bool:
    value = os.getenv("HH_HAUSHALTSBUCH_LIDL_ENABLED")
    if value is None:
        return True
    return value.strip().lower() in {"1", "true", "yes", "on"}
