"""query_portfolio — KI-Tool für die Krypto-Bestände & P&L des Nutzers (FIFO, EUR).

User-scoped über ctx.user_id: liefert nur die Holdings des fragenden Users.
Reines Tracking — kein Trading, kein Wallet-Zugriff.
"""
from __future__ import annotations

from hydrahive.tools.base import Tool, ToolContext, ToolResult

from . import portfolio

_DESCRIPTION = (
    "Fragt das Krypto-Portfolio des aktuellen Nutzers ab (manuell gepflegtes "
    "FIFO-Ledger, Werte in EUR). Liefert aktuelle Bestände je Coin (Menge, "
    "Ø-Einstand, aktueller Kurs, Wert), unrealisierten und realisierten Gewinn/"
    "Verlust sowie den Gesamtwert. Nutze es für Fragen wie 'Wie steht mein "
    "Portfolio?', 'Was ist mein Gewinn?' oder 'Wie viel Bitcoin halte ich?'."
)

_SCHEMA = {"type": "object", "properties": {}, "required": []}


def _fmt_eur(v: float | None) -> str:
    if v is None:
        return "—"
    return f"{v:,.2f} €"


def _line(p: dict) -> str:
    sym = p.get("symbol") or p.get("coin_id")
    qty = p.get("quantity") or 0.0
    parts = [f"{sym}: {qty:g} Stück", f"Wert {_fmt_eur(p.get('value'))}"]
    upnl = p.get("unrealized_pnl")
    if upnl is not None:
        parts.append(f"unrealisiert {upnl:+,.2f} € ({p.get('unrealized_pct', 0):+.1f} %)")
    return " · ".join(parts)


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    user = ctx.user_id
    if not user:
        return ToolResult.fail("Kein Nutzerkontext für die Portfolio-Abfrage.")
    try:
        summary = await portfolio.summary(user)
    except Exception as exc:
        return ToolResult.fail(f"Portfolio-Abruf fehlgeschlagen: {exc}")

    totals = summary["totals"]
    open_positions = [p for p in summary["positions"] if p.get("is_open")]
    if not open_positions:
        return ToolResult.ok({"message": "Keine offenen Positionen im Portfolio.", "count": 0})

    lines = [_line(p) for p in open_positions]
    header = (
        f"Gesamtwert {_fmt_eur(totals['value'])} · "
        f"unrealisiert {totals['unrealized_pnl']:+,.2f} € ({totals['unrealized_pct']:+.1f} %) · "
        f"realisiert {totals['realized_pnl']:+,.2f} €"
    )
    return ToolResult.ok({
        "currency": "EUR",
        "open_positions": len(open_positions),
        "summary": header,
        "data": "\n".join(lines),
    })


TOOL = Tool(
    name="query_portfolio",
    description=_DESCRIPTION,
    schema=_SCHEMA,
    execute=_execute,
    category="data",
)
