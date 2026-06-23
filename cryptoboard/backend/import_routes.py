"""CSV-Import-Routen — /api/modules/cryptoboard/portfolio/import/{preview,commit}.

Generischer Wallet-CSV-Importer (Option B). Zwei Schritte:
  preview  — CSV-Text rein → Mapping-Vorschlag + geparste Transaktionen +
             Symbol→CoinGecko-ID-Auflösung + Dedup-Markierung (was schon da ist)
  commit   — bestätigte Transaktionen (mit aufgelösten coin_ids) ins Ledger,
             Duplikate via import_hash übersprungen

Login-pflichtig, strikt user-scoped. Reines Tracking — kein Wallet-Zugriff.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded

from . import client, csv_import, portfolio_store as store
from .validators import ID_RE, ISO_RE

router = APIRouter()

Auth = Annotated[tuple[str, str], Depends(require_auth)]

_MAX_CSV_BYTES = 2_000_000  # 2 MB


class PreviewIn(BaseModel):
    csv: str = Field(min_length=1)
    mapping: dict[str, str | None] | None = None  # optionales Override


class CommitTx(BaseModel):
    coin_id: str = Field(min_length=1, max_length=80)
    symbol: str = Field(default="", max_length=20)
    name: str = Field(default="", max_length=120)
    kind: str = Field(min_length=1, max_length=20)
    quantity: float = Field(gt=0)
    price: float = Field(default=0.0, ge=0)
    fee: float = Field(default=0.0, ge=0)
    executed_at: str = Field(min_length=1, max_length=40)
    hash: str = Field(default="", max_length=64)


class CommitIn(BaseModel):
    transactions: list[CommitTx]


async def _resolve_symbols(symbols: list[str]) -> dict[str, dict | None]:
    """Symbol → bester CoinGecko-Treffer (kleinster market_cap_rank)."""
    out: dict[str, dict | None] = {}
    for sym in symbols:
        try:
            hits = await client.search(sym)
        except Exception:
            hits = []
        matches = [h for h in hits if (h.get("symbol") or "").upper() == sym.upper()]
        matches.sort(key=lambda h: h.get("market_cap_rank") or 10**9)
        best = matches[0] if matches else None
        out[sym] = {"id": best["id"], "name": best["name"], "symbol": best["symbol"]} if best else None
    return out


@router.post("/portfolio/import/preview")
async def import_preview(body: PreviewIn, auth: Auth) -> dict:
    user, _ = auth
    if len(body.csv.encode("utf-8")) > _MAX_CSV_BYTES:
        raise coded(status.HTTP_400_BAD_REQUEST, "csv_too_large")
    try:
        header, rows = csv_import.sniff(body.csv)
    except csv_import.ImportError as exc:
        raise coded(status.HTTP_400_BAD_REQUEST, str(exc))

    mapping = body.mapping or csv_import.guess_map(header)
    result = csv_import.parse_rows(rows, mapping)

    resolved = await _resolve_symbols(result["symbols"])
    hashes = [t["hash"] for t in result["transactions"]]
    already = store.existing_hashes(user, hashes)

    # Transaktionen mit Auflösung + Dedup-Flag anreichern
    for t in result["transactions"]:
        match = resolved.get(t["symbol"])
        t["coin_id"] = match["id"] if match else None
        t["coin_name"] = match["name"] if match else None
        t["resolved"] = match is not None
        t["duplicate"] = t["hash"] in already

    return {
        "header": header,
        "mapping": mapping,
        "fields": list(csv_import.FIELDS),
        "transactions": result["transactions"],
        "errors": result["errors"],
        "unresolved_symbols": sorted({t["symbol"] for t in result["transactions"] if not t["resolved"]}),
        "duplicate_count": sum(1 for t in result["transactions"] if t["duplicate"]),
    }


@router.post("/portfolio/import/commit")
def import_commit(body: CommitIn, auth: Auth) -> dict:
    user, _ = auth
    if not body.transactions:
        return {"ok": True, "imported": 0, "skipped": 0}

    incoming_hashes = [t.hash for t in body.transactions if t.hash]
    already = store.existing_hashes(user, incoming_hashes)

    imported = 0
    skipped = 0
    for t in body.transactions:
        if t.hash and t.hash in already:
            skipped += 1
            continue
        coin_id = t.coin_id.strip().lower()
        if not ID_RE.match(coin_id):
            skipped += 1
            continue
        if t.kind not in store.KINDS:
            skipped += 1
            continue
        if not ISO_RE.match(t.executed_at.strip()):
            skipped += 1
            continue
        try:
            store.add(
                user, coin_id=coin_id, symbol=t.symbol.strip().upper(),
                name=t.name.strip(), kind=t.kind, quantity=t.quantity,
                price=t.price, fee=t.fee, executed_at=t.executed_at.strip(),
                note="CSV-Import", import_hash=t.hash or None,
            )
            imported += 1
            already.add(t.hash)  # innerhalb desselben Commits nicht doppeln
        except ValueError:
            skipped += 1

    return {"ok": True, "imported": imported, "skipped": skipped}
