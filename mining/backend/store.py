"""Speicher: Kurs-Cache (module_mining_quotes) und Einstellungen (module_mining_config).

Bei einem Kryptex-Ausfall bleiben die letzten Werte stehen (``replace_quotes``
wird dann gar nicht aufgerufen); ``fetched_at`` zeigt, wie alt sie sind.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

from hydrahive.db.connection import db

from .profit import CoinQuote

REGIONS = ("global", "eu", "us", "br", "sg", "hk", "ru", "ae")
DEFAULTS: dict[str, Any] = {
    "kryptex_user": "",       # Benutzername oder Wallet; Login am Pool = "<user>/<rig>"
    "region": "eu",
    "switch_threshold": 0.05,  # Wechsel erst ab 5 % mehr Ertrag
    "min_runtime_min": 15,     # frühestens nach 15 min wechseln
    "prop_discount": 0.0,      # Abschlag für PROP-Coins (0..0.5)
    # Energie-Steuerung (E5): off | fixed | http
    "power_mode": "off",
    "power_fixed_w": 2000,
    "power_url": "",           # nur LAN, z. B. http://192.168.178.50/api/surplus
    "power_field": "",         # JSON-Pfad, z. B. data.surplus_w
    "power_scale": 1.0,        # z. B. 1000 wenn die Quelle kW liefert
    "power_reserve_w": 100,
    "power_min_minutes": 10,
    "power_stale_minutes": 15,
    "clore_dryrun": False,     # Clore-Probelauf: Marktplatz lesen und rechnen, nichts mieten (ab Werk aus)
}
POWER_MODES = ("off", "fixed", "http")
_FIELD_RE = re.compile(r"^[A-Za-z0-9_.\-]{0,100}$")
_USER_RE = re.compile(r"^[A-Za-z0-9._@+\-]{0,128}$")


_LIMITS = {"switch_threshold": (0.0, 1.0), "min_runtime_min": (1, 1440), "prop_discount": (0.0, 0.5),
           "power_fixed_w": (0, 1_000_000), "power_scale": (0.000001, 1_000_000), "power_reserve_w": (0, 100_000),
           "power_min_minutes": (1, 240), "power_stale_minutes": (1, 240)}
_INTS = {"min_runtime_min", "power_fixed_w", "power_reserve_w", "power_min_minutes", "power_stale_minutes"}


class ConfigError(ValueError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def replace_quotes(quotes: list[CoinQuote]) -> None:
    """Abruf-Ergebnis übernehmen. Leere Liste ändert nichts (Ausfallschutz)."""
    if not quotes:
        return
    ts = _now()
    with db() as c:
        for q in quotes:
            c.execute(
                "INSERT INTO module_mining_quotes (coin, name, algo, fee, fee_type, profit_per_hs_day,"
                " price_usd, estimated, fetched_at) VALUES (?,?,?,?,?,?,?,?,?)"
                " ON CONFLICT(coin) DO UPDATE SET name=excluded.name, algo=excluded.algo,"
                " fee=excluded.fee, fee_type=excluded.fee_type,"
                " profit_per_hs_day=excluded.profit_per_hs_day, price_usd=excluded.price_usd,"
                " estimated=excluded.estimated, fetched_at=excluded.fetched_at",
                (q.coin, q.name, q.algo, q.fee, q.fee_type, q.profit_per_hs_day,
                 q.price_usd, int(q.estimated), ts),
            )


def load_quotes() -> tuple[list[CoinQuote], str | None]:
    """(Quotes, ältester Abrufzeitpunkt) — None, wenn noch nie abgerufen."""
    with db() as c:
        rows = c.execute("SELECT * FROM module_mining_quotes ORDER BY coin").fetchall()
    quotes = [
        CoinQuote(coin=r["coin"], name=r["name"], algo=r["algo"], fee=r["fee"],
                  fee_type=r["fee_type"], profit_per_hs_day=r["profit_per_hs_day"],
                  price_usd=r["price_usd"], estimated=bool(r["estimated"]))
        for r in rows
    ]
    oldest = min((r["fetched_at"] for r in rows), default=None)
    return quotes, oldest


def set_usd_per_eur(rate: float) -> None:
    """EZB-Referenzkurs (1 EUR = rate USD). Intern, nicht über die API änderbar."""
    with db() as c:
        c.execute(
            "INSERT INTO module_mining_config (key, value, updated_at) VALUES ('_usd_per_eur', ?, ?)"
            " ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
            (json.dumps(float(rate)), _now()),
        )


def get_usd_per_eur() -> float | None:
    with db() as c:
        row = c.execute("SELECT value FROM module_mining_config WHERE key='_usd_per_eur'").fetchone()
    return float(json.loads(row["value"])) if row else None


def get_config() -> dict[str, Any]:
    with db() as c:
        rows = c.execute("SELECT key, value FROM module_mining_config").fetchall()
    cfg = dict(DEFAULTS)
    for r in rows:
        if r["key"] in DEFAULTS:
            cfg[r["key"]] = json.loads(r["value"])
    return cfg


def _validate(key: str, value: Any) -> Any:
    if key == "kryptex_user":
        if not isinstance(value, str) or not _USER_RE.match(value.strip()):
            raise ConfigError("kryptex_user_invalid")
        return value.strip()
    if key == "region":
        if value not in REGIONS:
            raise ConfigError("region_invalid")
        return value
    if key == "clore_dryrun":
        if not isinstance(value, bool):
            raise ConfigError("clore_dryrun_invalid")
        return value
    if key == "power_mode":
        if value not in POWER_MODES:
            raise ConfigError("power_mode_invalid")
        return value
    if key == "power_url":
        if value == "":
            return ""
        from .power_source import validate_url
        try:
            return validate_url(str(value).strip())
        except ValueError as exc:
            raise ConfigError(str(exc)) from exc
    if key == "power_field":
        if not isinstance(value, str) or not _FIELD_RE.match(value):
            raise ConfigError("power_field_invalid")
        return value
    lo, hi = _LIMITS[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not lo <= value <= hi:
        raise ConfigError(f"{key}_out_of_range")
    return int(value) if key in _INTS else float(value)


def update_config(changes: dict[str, Any]) -> dict[str, Any]:
    """Nur bekannte Schlüssel, alle vorher geprüft — sonst ändert sich nichts."""
    unknown = set(changes) - set(DEFAULTS)
    if unknown:
        raise ConfigError("unknown_key")
    clean = {k: _validate(k, v) for k, v in changes.items()}
    with db() as c:
        for k, v in clean.items():
            c.execute(
                "INSERT INTO module_mining_config (key, value, updated_at) VALUES (?, ?, ?)"
                " ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
                (k, json.dumps(v), _now()),
            )
    return get_config()
