"""query_crypto_price — KI-Tool für aktuelle Krypto-Kurse (CoinGecko)."""
from __future__ import annotations

from hydrahive.tools.base import Tool, ToolContext, ToolResult

from . import client
from .validators import ID_RE, VS_RE

_DESCRIPTION = (
    "Fragt aktuelle Kryptowährungs-Kurse ab (CoinGecko). Gib eine oder mehrere "
    "Coins als CoinGecko-IDs an (z.B. 'bitcoin', 'ethereum', 'solana'). "
    "Liefert Preis, 24h-/7d-Änderung, Marktkapitalisierung und Volumen. "
    "Nutze dieses Tool für Fragen wie 'Was kostet Bitcoin?'. Standard-Währung EUR."
)

_SCHEMA = {
    "type": "object",
    "properties": {
        "coins": {
            "type": "array",
            "items": {"type": "string"},
            "description": "CoinGecko-IDs (Kleinbuchstaben), z.B. ['bitcoin','ethereum'].",
        },
        "vs_currency": {
            "type": "string",
            "description": "ISO-Währung, z.B. 'eur' oder 'usd'. Default 'eur'.",
        },
    },
    "required": ["coins"],
}

_MAX_COINS = 25


def _format(r: dict, vs: str) -> str:
    price = r.get("price")
    ch24 = r.get("change_24h")
    ch7 = r.get("change_7d")
    cap = r.get("market_cap")
    parts = [f"{r.get('name')} ({r.get('symbol')}): {price} {vs}"]
    if ch24 is not None:
        parts.append(f"24h {ch24:+.2f}%")
    if ch7 is not None:
        parts.append(f"7d {ch7:+.2f}%")
    if cap is not None:
        parts.append(f"Marktcap {cap}")
    return " · ".join(parts)


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    raw = args.get("coins") or []
    coins = [str(c).strip().lower() for c in raw if str(c).strip()]
    coins = [c for c in coins if ID_RE.match(c)][:_MAX_COINS]
    if not coins:
        return ToolResult.fail("Keine gültigen Coin-IDs angegeben (z.B. 'bitcoin').")

    vs = (args.get("vs_currency") or "eur").strip().lower()
    if not VS_RE.match(vs):
        vs = "eur"

    try:
        rows = await client.markets(vs, ids=coins)
    except Exception as exc:
        return ToolResult.fail(f"Kurs-Abruf fehlgeschlagen: {exc}")

    if not rows:
        return ToolResult.ok({"message": "Keine Kurse gefunden.", "count": 0})

    lines = [_format(r, vs.upper()) for r in rows]
    return ToolResult.ok({"count": len(rows), "currency": vs.upper(), "data": "\n".join(lines)})


TOOL = Tool(
    name="query_crypto_price",
    description=_DESCRIPTION,
    schema=_SCHEMA,
    execute=_execute,
    category="data",
)
