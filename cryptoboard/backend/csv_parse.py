"""CSV-Wert-Parser — reine Konvertierung einzelner Zellwerte, keine I/O.

Zahlen (DE/EN-Format), Datumsangaben (viele Wallet-Formate), Buy/Sell/Transfer-
Klassifizierung und Symbol-Bereinigung. Von csv_import genutzt; getrennt, damit
jede Datei eine Verantwortung behält (Werte-Parsing vs. CSV-Struktur).
"""
from __future__ import annotations

import re
from datetime import datetime

# Buy/Sell/Transfer-Erkennung aus dem kind-Rohwert (lowercase Teilstring).
# Reihenfolge in classify_kind: transfer → sell → buy. "verkauf" enthält "kauf",
# darum MUSS sell vor buy geprüft werden. Kurze mehrdeutige Tokens (in/out)
# bewusst NICHT als Buy/Sell — die landen über die Transfer-Marker.
_BUY = ("buy", "kauf", "purchase", "long", "credit")
_SELL = ("sell", "verkauf", "sale", "short", "debit")
_TRANSFER_IN = ("deposit", "eingang", "receive", "received", "transfer in", "transfer-in",
                "topup", "top-up", "top up", "incoming", "reward", "airdrop", "payin", "pay-in")
_TRANSFER_OUT = ("withdraw", "withdrawal", "ausgang", "send", "sent", "transfer out",
                 "transfer-out", "payout", "payment", "outgoing")

_DATE_FORMATS = (
    "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d",
    "%d.%m.%Y %H:%M:%S", "%d.%m.%Y %H:%M", "%d.%m.%Y", "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y", "%m/%d/%Y %H:%M:%S", "%m/%d/%Y", "%Y/%m/%d",
)

_FIAT_QUOTES = ("EUR", "USD", "USDT", "USDC", "GBP", "BUSD")


def parse_number(raw: str) -> float | None:
    """Robust gegen 1.234,56 (DE) und 1,234.56 (EN) sowie Währungssymbole."""
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    s = re.sub(r"[^\d,.\-]", "", s)  # €, $, Leerzeichen, Symbole raus
    if not s or s in ("-", ".", ","):
        return None
    if "," in s and "." in s:
        # Letztes Trennzeichen ist das Dezimaltrennzeichen
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")   # DE: 1.234,56
        else:
            s = s.replace(",", "")                       # EN: 1,234.56
    elif "," in s:
        s = s.replace(",", ".")                          # nur Komma → Dezimal
    try:
        return float(s)
    except ValueError:
        return None


def parse_date(raw: str) -> str | None:
    """Liefert ISO-Datum (YYYY-MM-DD) oder None."""
    if not raw:
        return None
    s = str(raw).strip().replace("Z", "")
    s = re.sub(r"[+]\d{2}:?\d{2}$", "", s).strip()  # Zeitzone abschneiden
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    m = re.match(r"(\d{4}-\d{2}-\d{2})", s)
    return m.group(1) if m else None


def classify_kind(raw: str) -> str | None:
    """Mappt einen kind-Rohwert auf buy/sell/transfer_in/transfer_out."""
    if not raw:
        return None
    low = str(raw).strip().lower()
    if any(h in low for h in _TRANSFER_IN) and "trade" not in low and "buy" not in low:
        return "transfer_in"
    if any(h in low for h in _TRANSFER_OUT) and "trade" not in low and "sell" not in low:
        return "transfer_out"
    # Sell VOR Buy: "verkauf" enthält "kauf".
    if any(h in low for h in _SELL):
        return "sell"
    if any(h in low for h in _BUY):
        return "buy"
    return None


def clean_symbol(raw: str) -> str:
    """Extrahiert das Basis-Symbol (BTC aus 'BTC/EUR', 'BTCEUR', 'BTC-EUR')."""
    s = str(raw or "").strip().upper()
    for sep in ("/", "-", "_"):
        if sep in s:
            return s.split(sep)[0].strip()
    for quote in _FIAT_QUOTES:
        if s.endswith(quote) and len(s) > len(quote):
            return s[: -len(quote)]
    return s
