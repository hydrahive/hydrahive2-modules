"""Alchemy-Key-Verwaltung pro Nutzer — Vorab-Test VOR dem Speichern.

Speicherung über hydrahive.credentials.store (Muster: network/backend/creds.py).
Credential-Name "cryptoboard-alchemy", Typ "bearer", url_pattern passt auf
"https://*.g.alchemy.com/*" (has_concrete_host akzeptiert "*." + Domain mit
Punkt — siehe tests/test_alchemy_key.py).

Der Key wird NIE im Klartext zurückgegeben (nur maskiert) und NIE geloggt.
Scheitert der Vorab-Test, wird NICHTS gespeichert (set_key ist atomar aus
Sicht des Aufrufers: Test zuerst, Speichern nur bei Erfolg).
"""
from __future__ import annotations

from hydrahive.credentials.models import Credential
from hydrahive.credentials.store import delete_credential, get_credential, save_credential

from . import alchemy_client

CREDENTIAL_NAME = "cryptoboard-alchemy"
_URL_PATTERN = "https://*.g.alchemy.com/*"
_TEST_CHAIN = "base"


class KeyTestFailed(RuntimeError):
    """Der Vorab-Test des Keys ist gescheitert. `code` ist der Fehlercode für die API."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _mask(key: str) -> str:
    """'abcd…wxyz'-Maskierung — nie mehr als Anfang/Ende, nie die Länge genau genug zum Raten."""
    if len(key) <= 8:
        return "…"
    return f"{key[:4]}…{key[-4:]}"


def _classify_http_error(status_code: int, body: str) -> str:
    if status_code == 401:
        return "alchemy_key_invalid"
    if status_code == 403:
        low = body.lower()
        if any(w in low for w in ("network", "plan", "tier", "not enabled", "not supported")):
            return "alchemy_base_not_enabled"
        return "alchemy_key_invalid"
    return "alchemy_test_failed"


def _classify_api_error(message: str) -> str:
    low = message.lower()
    if any(w in low for w in ("network", "plan", "tier", "not enabled", "not supported")):
        return "alchemy_base_not_enabled"
    return "alchemy_test_failed"


async def test_key(key: str) -> None:
    """Prüft einen Key mit einem minimalen, lesenden Aufruf (eth_blockNumber auf Base).

    Wirft KeyTestFailed mit einem der Codes:
      alchemy_key_invalid      — 401/403 ohne Plan-/Netz-Hinweis
      alchemy_base_not_enabled — Alchemy-Fehlertext deutet auf Plan-/Netzwerk-
                                 Einschränkung hin (Base evtl. nicht freigegeben)
      alchemy_network_error    — kein HTTP-Status (Timeout/Verbindung)
      alchemy_test_failed      — sonstiger, nicht klassifizierbarer Fehler
      cryptoboard_onchain_disabled — Kill-Switch aus
    """
    try:
        await alchemy_client.call(_TEST_CHAIN, key, "eth_blockNumber", [])
    except alchemy_client.AlchemyDisabled as exc:
        raise KeyTestFailed("cryptoboard_onchain_disabled") from exc
    except alchemy_client.AlchemyHttpError as exc:
        body = getattr(exc, "body", "") or ""
        raise KeyTestFailed(_classify_http_error(exc.status_code, body)) from exc
    except alchemy_client.AlchemyApiError as exc:
        raise KeyTestFailed(_classify_api_error(exc.rpc_message)) from exc
    except alchemy_client.AlchemyNetworkError as exc:
        raise KeyTestFailed("alchemy_network_error") from exc


async def set_key(username: str, key: str) -> tuple[bool, str]:
    """Testet den Key, speichert ihn NUR bei Erfolg. Rückgabe (ok, code)."""
    key = key.strip()
    if not key:
        return False, "alchemy_key_empty"
    try:
        await test_key(key)
    except KeyTestFailed as exc:
        return False, exc.code
    cred = Credential(name=CREDENTIAL_NAME, type="bearer", value=key, url_pattern=_URL_PATTERN,
                       description="Alchemy-Key für On-Chain-Trade-Import (nur lesend)")
    ok, err = save_credential(username, cred)
    if not ok:
        return False, err or "alchemy_key_save_failed"
    return True, ""


def status(username: str) -> dict:
    """Nie der Klartext — nur ob gesetzt und maskiert."""
    cred = get_credential(username, CREDENTIAL_NAME)
    if cred is None or not cred.value:
        return {"set": False, "masked": None}
    return {"set": True, "masked": _mask(cred.value)}


def delete_key(username: str) -> bool:
    return delete_credential(username, CREDENTIAL_NAME)


def get_key(username: str) -> str | None:
    """Für interne Aufrufer (alchemy_client-Nutzung in Teil B) — nie nach außen zurückgeben."""
    cred = get_credential(username, CREDENTIAL_NAME)
    return cred.value if cred and cred.value else None
