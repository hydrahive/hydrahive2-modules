"""Kiosk (Statuszentrale, Etappe S1): Seite für den Browser auf dem Gehäuse-Display und der „Zurück“-Knopf.

Der Kiosk-Browser hat keinen HydraHive-Login. Er kommt über die Geräte-Routen des Kerns (`/api/module-device/vitrine/…`,
mit Rate-Limit) und braucht den Kiosk-Schlüssel (<daten>/kiosk.key, 0600, vom Installer erzeugt). Zusätzlich gilt: nur von
127.0.0.1/::1. Ab S2 zeigt die Seite die Statuszentrale; Daten holt sie über die Route `data` (dash_data).
"""
from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path

from renderer import mode

MIN_KEY = 32
LOCAL = frozenset({"127.0.0.1", "::1"})
HERE = Path(__file__).parent
PAGE_FILES = ("kiosk_page.html", "kiosk_chat.js", "kiosk_bt.js")


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


def page_version() -> str:
    """Version der Kiosk-Seite = Hash über ihre Dateien. Steht in der Seite und in /data. Weicht sie ab, hat ein Update
    die Seite geändert, und der Kiosk lädt sich neu (Fund 20.10.2026: gemischte Seite, 18 h „antwortet nicht“)."""
    h = hashlib.sha256()
    for name in PAGE_FILES:
        h.update((HERE / name).read_bytes())
    return h.hexdigest()[:16]


def page(key: str) -> str:
    """Statuszentrale (S2): statische Seite aus dem Modul; der Schlüssel wird als JS-String eingesetzt (json + </ entschärft)."""
    k = json.dumps(key)[1:-1].replace("</", "<\\/")
    js = "\n".join((HERE / n).read_text(encoding="utf-8").replace("</", "<\\/") for n in ("kiosk_chat.js", "kiosk_bt.js"))
    html = (HERE / "kiosk_page.html").read_text(encoding="utf-8").replace("__KEY__", k).replace("__VERSION__", page_version())
    return html.replace("</script></html>", "\n" + js + "</script></html>", 1)
