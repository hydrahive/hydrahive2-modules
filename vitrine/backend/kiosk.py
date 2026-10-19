"""Kiosk (Statuszentrale, Etappe S1): Seite für den Browser auf dem Gehäuse-Display und der „Zurück“-Knopf.

Der Kiosk-Browser hat keinen HydraHive-Login. Er kommt über die Geräte-Routen des Kerns (`/api/module-device/vitrine/…`,
mit Rate-Limit) und braucht den Kiosk-Schlüssel (<daten>/kiosk.key, 0600, vom Installer erzeugt). Zusätzlich gilt: nur von
127.0.0.1/::1. Ab S2 zeigt die Seite die Statuszentrale; Daten holt sie über die Route `data` (dash_data).
"""
from __future__ import annotations

import hmac
import json
from pathlib import Path

from renderer import mode

MIN_KEY = 32
LOCAL = frozenset({"127.0.0.1", "::1"})


def key_ok(data_dir: Path, given: str | None) -> bool:
    try:
        want = (data_dir / "kiosk.key").read_text().strip()
    except OSError:
        return False
    if len(want) < MIN_KEY or not given:
        return False
    return hmac.compare_digest(want.encode(), given.encode())


def local_ok(host: str | None) -> bool:
    return host in LOCAL


def back(data_dir: Path) -> None:
    mode.request_back(data_dir)


def page(key: str) -> str:
    """Statuszentrale (S2): statische Seite aus dem Modul; der Schlüssel wird als JS-String eingesetzt (json + </ entschärft)."""
    k = json.dumps(key)[1:-1].replace("</", "<\\/")
    here = Path(__file__).parent
    chat_js = (here / "kiosk_chat.js").read_text(encoding="utf-8").replace("</", "<\\/")
    html = (here / "kiosk_page.html").read_text(encoding="utf-8").replace("__KEY__", k)
    return html.replace("</script></html>", "\n" + chat_js + "</script></html>", 1)
