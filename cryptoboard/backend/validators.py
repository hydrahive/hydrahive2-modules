"""Geteilte Eingabe-Validierung — Coin-ID / Währung / Tage / News-Felder.

Diese Werte fließen in Upstream-API-URLs/Params (CoinGecko, CryptoCompare);
zentral validiert, eine Quelle für Routen UND Agent-Tool.
"""
from __future__ import annotations

import re

ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,80}$")
VS_RE = re.compile(r"^[a-z]{2,10}$")
DAYS_RE = re.compile(r"^(\d{1,5}|max)$")
CATS_RE = re.compile(r"^[A-Za-z0-9,]{0,100}$")
LANG_RE = re.compile(r"^[A-Za-z]{2,5}$")
# ISO-Zeitstempel: Datum, optional mit Zeit (T HH:MM[:SS]) und optionalem Z.
ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}([T ]\d{2}:\d{2}(:\d{2})?Z?)?$")
