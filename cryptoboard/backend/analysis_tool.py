"""query_crypto_analysis — KI-Tool für technische Analyse + Markt-Sentiment.

Holt den CoinGecko-Chart eines Coins, berechnet RSI/MACD/SMA und kombiniert das
mit dem Fear & Greed Index zu einer kompakten, textuellen Einschätzung. Liefert
Fakten (keine Anlageberatung); EUR als Default-Währung.
"""
from __future__ import annotations

from hydrahive.tools.base import Tool, ToolContext, ToolResult

from . import client, indicators, sentiment
from .validators import ID_RE, VS_RE

_DESCRIPTION = (
    "Liefert eine technische Analyse zu einer Kryptowährung: aktueller RSI(14), "
    "MACD-Signal (bullish/bearish), Lage zu den gleitenden Durchschnitten "
    "(SMA20/SMA50) plus den globalen Fear & Greed Index. Gib die CoinGecko-ID an "
    "(z.B. 'bitcoin'). Nutze es für Fragen wie 'Wie ist die Lage bei Ethereum?' "
    "oder 'Ist Bitcoin überkauft?'. Keine Anlageberatung — nur Indikator-Fakten."
)

_SCHEMA = {
    "type": "object",
    "properties": {
        "coin": {"type": "string", "description": "CoinGecko-ID, z.B. 'bitcoin'."},
        "vs_currency": {"type": "string", "description": "ISO-Währung, Default 'eur'."},
    },
    "required": ["coin"],
}


def _last(series: list) -> float | None:
    for v in reversed(series):
        if v is not None:
            return v
    return None


def _rsi_label(rsi: float) -> str:
    if rsi >= 70:
        return "überkauft"
    if rsi <= 30:
        return "überverkauft"
    return "neutral"


def _build_report(prices: list[float]) -> dict:
    ind = indicators.compute_all(prices)
    last_price = prices[-1]
    rsi = _last(ind["rsi14"])
    macd = _last(ind["macd"])
    signal = _last(ind["macd_signal"])
    sma20 = _last(ind["sma20"])
    sma50 = _last(ind["sma50"])

    facts = []
    if rsi is not None:
        facts.append(f"RSI(14) {rsi:.1f} ({_rsi_label(rsi)})")
    if macd is not None and signal is not None:
        facts.append(f"MACD {'bullish' if macd >= signal else 'bearish'}")
    if sma20 is not None:
        facts.append(f"Kurs {'über' if last_price >= sma20 else 'unter'} SMA20")
    if sma50 is not None:
        facts.append(f"Kurs {'über' if last_price >= sma50 else 'unter'} SMA50")
    return {"rsi": rsi, "macd_bullish": (macd is not None and signal is not None and macd >= signal),
            "facts": facts}


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    coin = str(args.get("coin") or "").strip().lower()
    if not ID_RE.match(coin):
        return ToolResult.fail("Ungültige Coin-ID (z.B. 'bitcoin').")
    vs = (args.get("vs_currency") or "eur").strip().lower()
    if not VS_RE.match(vs):
        vs = "eur"

    try:
        raw = await client.market_chart(coin, vs, "90")
    except Exception as exc:
        return ToolResult.fail(f"Chart-Abruf fehlgeschlagen: {exc}")
    prices = [float(p[1]) for p in raw if isinstance(p, list) and len(p) >= 2]
    if len(prices) < 30:
        return ToolResult.fail("Zu wenige Kursdaten für eine Analyse.")

    report = _build_report(prices)

    fng_txt = "—"
    try:
        fng = await sentiment.fear_greed(1)
        cur = fng.get("current") or {}
        if cur.get("value") is not None:
            fng_txt = f"{cur['value']} ({cur.get('classification') or '—'})"
    except Exception:
        pass

    return ToolResult.ok({
        "coin": coin,
        "currency": vs.upper(),
        "fear_greed": fng_txt,
        "analysis": " · ".join(report["facts"]) or "Keine Indikatoren verfügbar.",
    })


TOOL = Tool(
    name="query_crypto_analysis",
    description=_DESCRIPTION,
    schema=_SCHEMA,
    execute=_execute,
    category="data",
)
