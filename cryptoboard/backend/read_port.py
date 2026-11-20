"""Read-Port für modulübergreifenden Lesezugriff (Haushaltsbuch V9 Task 3.1, v2: Etappe A2).

Einzige Stelle, die andere Module importieren dürfen (vgl.
haushaltsbuch/PLAN-V9-AUSWERTUNGEN-CRYPTO.md Task 3.1 und
VERTRAG-PORT-V2.md, Etappe A). Es gibt im Repo keine eigenständige
CONTRACT.md für modulübergreifende Zugriffe — dieser Docstring IST der
Vertrag.
Keine Schreibfunktionen, keine Routen — reine Lese-Fassade über die bestehende
Portfolio-/Wertverlauf-Logik (portfolio.py, valuation.py, portfolio_store.py,
price_history_store.py) UND über die Wallet-Logik (wallets.py,
read_port_wallets.py). Schlüssel ist immer der Core-Username (require_auth
liefert (username, role)); Cryptoboard hat genau EIN Ledger pro User und
KEINEN Freigabe-Mechanismus — darum ist "default" die einzige gültige
portfolio_id.

Geldwerte: intern (REAL/float, EUR) wie im restlichen Modul — nach außen für
Geldbeträge ausschließlich Integer-Cent (ROUND_HALF_EVEN über Decimal(str(x)),
nie direkt über float, um Rundungs-Bias zu vermeiden). `quantity` bleibt als
Decimal-String (Kryptomengen sind keine Cent-Beträge).

v2 (Etappe A2, VERTRAG-PORT-V2.md): zusätzlich wallet_addresses_for() und
wallet_holdings() — Bestand je Coin und EUR-Wert für EIGENE Adressen (nicht
nur der Portfolio-Gesamtwert wie in v1). Implementiert in read_port_wallets.py
(Datei-Größenlimit), hier nur re-exportiert/verdrahtet (EINE Einstiegsdatei
bleibt bestehen; die Cent-Rundung _to_minor lebt weiterhin nur hier).

v3 (Etappe B, VERTRAG-B.md Punkt 3): zusätzlich ledger_moves() — Swap-/
Zahlungs-Bewegungen aus dem bestehenden On-Chain-Ledger (Umbuchung Tron->EVM
bzw. Kartenzahlung/Abgang), für das Haushaltsbuch. Implementiert in
read_port_moves.py (Datei-Größenlimit), hier nur re-exportiert/verdrahtet.

Zugriff aus Haushaltsbuch: Der Kern lädt Modul-Backends als
sys.modules["hhmod_<id>"]; Haushaltsbuch importiert
importlib.import_module("hhmod_cryptoboard.read_port") NUR wenn
hydrahive.modules.registry.REGISTRY.get("cryptoboard") existiert, .loaded
True ist und PORT_VERSION == 3 passt (v2: == 2, v1: == 1). Sonst eigener
Kill-Switch dort (CryptoBridgeUnavailable + letzter Snapshot), nicht hier.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import ROUND_HALF_EVEN, Decimal

from . import portfolio, portfolio_store as store, valuation
from . import price_history_store as price_store
from .read_port_moves import ledger_moves as _ledger_moves_impl
from .read_port_wallets import WalletAddressNotFound, wallet_addresses_for
from .read_port_wallets import wallet_holdings as _wallet_holdings_impl

PORT_VERSION = 3

__all__ = [
    "PORT_VERSION", "PortfolioNotFound", "PortfolioUnavailable", "WalletAddressNotFound",
    "ledger_moves", "portfolios_for", "portfolio_value", "trades", "value_series",
    "wallet_addresses_for", "wallet_holdings",
]

_DEFAULT_PORTFOLIO_ID = "default"
_CURRENCY = "EUR"


class PortfolioNotFound(LookupError):
    """Portfolio-ID unbekannt ODER gehört nicht dem User — bewusst nicht
    unterscheidbar (kein Existenz-Leak nach außen)."""


class PortfolioUnavailable(RuntimeError):
    """Kursquelle nicht erreichbar o. ä. — Daten könnten unvollständig sein."""


def _check_portfolio_id(portfolio_id: str) -> None:
    """Einzige gültige ID ist "default" (ein Ledger pro User, keine Freigabe).

    Wirft PortfolioNotFound statt eines spezifischeren Fehlers, damit der
    Aufrufer nicht zwischen "falsche ID" und "fremdes Portfolio" unterscheiden
    kann (kein Existenz-Leak).
    """
    if portfolio_id != _DEFAULT_PORTFOLIO_ID:
        raise PortfolioNotFound(portfolio_id)


def _to_minor(amount: float) -> int:
    """EUR-Betrag (float) → Integer-Cent, ROUND_HALF_EVEN über Decimal(str(x)).

    Decimal(str(x)) statt Decimal(x): vermeidet die Binär-Float-Artefakte
    (z.B. Decimal(0.1) == 0.1000000000000000055511151231257827021181583404541015625),
    rundet stattdessen auf Basis der üblichen Dezimal-Darstellung.
    """
    cents = (Decimal(str(amount)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_EVEN)
    return int(cents)


def _quantity_str(qty: float) -> str:
    """Krypto-Menge als Decimal-String (keine Cent-Rundung, kein Float nach außen)."""
    return str(Decimal(str(qty)))


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def portfolios_for(username: str) -> list[dict]:
    """Liste der Portfolios eines Users — immer genau eines ("default"), auch
    wenn der User (noch) keine Transaktionen hat."""
    return [{"id": _DEFAULT_PORTFOLIO_ID, "label": "Portfolio", "currency": _CURRENCY}]


async def portfolio_value(username: str, portfolio_id: str) -> dict:
    """Aktueller Gesamtwert eines Portfolios in Integer-Cent (EUR).

    `complete` ist False, wenn für mindestens eine offene Position (quantity
    > 0) kein aktueller Kurs geliefert wurde — der Wert ist dann eine
    Untergrenze, kein vollständiger Portfoliowert.

    Wirft PortfolioUnavailable NUR, wenn der Summary-Aufruf selbst scheitert
    (unerwarteter Fehler); ein bloßer Kursausfall einzelner Coins wird über
    `complete=False` abgebildet, nicht über eine Exception — portfolio.summary()
    fängt Kursfehler bereits intern ab und liefert price=None.
    """
    _check_portfolio_id(portfolio_id)
    try:
        data = await portfolio.summary(username)
    except Exception as exc:  # unerwarteter Fehler in der Summary-Berechnung
        raise PortfolioUnavailable(str(exc)) from exc

    positions = data["positions"]
    open_positions = [p for p in positions if p["is_open"]]
    complete = all(p.get("price") is not None for p in open_positions)

    return {
        "portfolio_id": portfolio_id,
        "currency": _CURRENCY,
        "value_minor": _to_minor(data["totals"]["value"]),
        "as_of": _now_iso(),
        "complete": complete,
        "position_count": data["totals"]["position_count"],
    }


def trades(
    username: str,
    portfolio_id: str,
    *,
    since: str | None = None,
    limit: int = 1000,
) -> list[dict]:
    """Chronologische Trade-Liste (keine Floats für Geld nach außen).

    `quantity` als Decimal-String, `gross_minor`/`fee_minor` als Integer-Cent.
    `since` filtert auf executed_at >= since (ISO-String-Vergleich, wie die
    Speicherung selbst — lexikographisch korrekt für ISO-8601).
    """
    _check_portfolio_id(portfolio_id)
    rows = store.list_for(username)
    if since:
        rows = [r for r in rows if str(r.get("executed_at") or "") >= since]
    rows = rows[:limit] if limit is not None else rows

    out: list[dict] = []
    for r in rows:
        qty = float(r["quantity"])
        price = float(r.get("price") or 0.0)
        fee = float(r.get("fee") or 0.0)
        out.append({
            "ref": f"cb:{r['id']}",
            "kind": r["kind"],
            "coin_id": r["coin_id"],
            "symbol": r.get("symbol") or "",
            "quantity": _quantity_str(qty),
            "gross_minor": _to_minor(qty * price),
            "fee_minor": _to_minor(fee),
            "executed_at": r["executed_at"],
            "import_hash": r.get("import_hash"),
        })
    return out


async def value_series(
    username: str,
    portfolio_id: str,
    *,
    start: date,
    end: date,
) -> list[dict]:
    """Monatsend-Werte (Integer-Cent) über die vorhandene valuation/
    price_history-Logik — kein eigener Berechnungsweg.

    Nutzt die TÄGLICHE Wertreihe aus valuation.value_series (gleiche Logik wie
    die Wertverlauf-Route) und reduziert sie auf den letzten verfügbaren Tag
    jedes Kalendermonats im Fenster [start, end]. Kurse kommen ausschließlich
    aus dem bestehenden Cache (price_history_store) — kein eigener Netz-Call,
    daher auch hier keine Exception bei Kursausfall: fehlende Tage/Monate
    werden einfach ausgelassen (die aufrufende Seite erkennt das an der
    Lückenhaftigkeit der Liste, analog zu `complete` bei portfolio_value).
    """
    _check_portfolio_id(portfolio_id)
    txs = store.list_for(username)
    coin_ids = sorted({t["coin_id"] for t in txs if t.get("coin_id")})
    prices = {cid: price_store.get_series(cid) for cid in coin_ids}

    daily = valuation.value_series(txs, prices, end.strftime("%Y-%m-%d"))
    start_str = start.strftime("%Y-%m-%d")
    end_str = end.strftime("%Y-%m-%d")
    in_range = [p for p in daily if start_str <= p["day"] <= end_str]

    # Letzter Tag je Monat (daily ist chronologisch aufsteigend sortiert).
    by_month: dict[str, dict] = {}
    for point in in_range:
        month = point["day"][:7]
        by_month[month] = point  # letzter gewinnt (Überschreiben in Reihenfolge)

    return [
        {"month": month, "value_minor": _to_minor(point["value"])}
        for month, point in sorted(by_month.items())
    ]


async def wallet_holdings(username: str, address_ids: list[int]) -> dict:
    """Bestand je Coin + EUR-Wert für EIGENE Adressen (v2). WalletAddressNotFound bei
    fremder/unbekannter address_id, PortfolioUnavailable bei unerwartetem Abruf-Fehler;
    ein bloßer Kursausfall einzelner Coins wird über complete=False abgebildet (wie
    portfolio_value), keine Exception."""
    try:
        return await _wallet_holdings_impl(
            username, address_ids, to_minor=_to_minor, quantity_str=_quantity_str, now_iso=_now_iso)
    except WalletAddressNotFound:
        raise
    except Exception as exc:
        raise PortfolioUnavailable(str(exc)) from exc


def ledger_moves(username: str, *, since: str | None = None, limit: int = 5000) -> list[dict]:
    """Swap-/Zahlungs-Bewegungen aus dem On-Chain-Ledger (v3). Reine Lese-Funktion, kein Netz —
    Fehler im Ledger-Zugriff selbst sind ein Programmierfehler, keine erwartete Ausnahme."""
    return _ledger_moves_impl(username, since=since, limit=limit, to_minor=_to_minor, quantity_str=_quantity_str)
