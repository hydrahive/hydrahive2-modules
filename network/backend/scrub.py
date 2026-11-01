"""Geheimnisse aus UniFi-Antworten entfernen, bevor irgendetwas damit passiert.

UniFi legt Schlüssel und Passwörter in Feldern ab, deren Name mit „x_“ beginnt (z. B. rest/wlanconf → x_passphrase =
WLAN-Passwort, stat/device → x_authkey). Am 01.11.2026 stand so ein Passwort ungefiltert in einer Ausgabe – deshalb
läuft jede Antwort der Dream Machine zuerst hierdurch (unifi_client.Udm).
"""
from __future__ import annotations

from typing import Any


def scrub(o: Any) -> Any:
    if isinstance(o, dict):
        return {k: scrub(v) for k, v in o.items() if not (isinstance(k, str) and k.startswith("x_"))}
    if isinstance(o, list):
        return [scrub(v) for v in o]
    return o
