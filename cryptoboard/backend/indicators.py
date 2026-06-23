"""Technische Indikatoren — reine Funktionen über Preisreihen, keine I/O.

Arbeitet auf einer einfachen Liste von Schlusskursen (chronologisch aufsteigend).
Liefert pro Indikator eine Reihe gleicher Länge wie der Input; Werte, die mangels
Datenhistorie nicht berechenbar sind, sind None. So bleibt die zeitliche
Ausrichtung mit der Preisreihe (und damit dem Chart) erhalten.

Implementiert: SMA, EMA, RSI (Wilder), MACD (12/26/9). Keine externen Libs —
bewusst dependency-frei und vollständig unit-testbar.
"""
from __future__ import annotations


def sma(prices: list[float], period: int) -> list[float | None]:
    """Simple Moving Average. Erste (period-1) Werte sind None."""
    out: list[float | None] = [None] * len(prices)
    if period <= 0:
        return out
    run = 0.0
    for i, p in enumerate(prices):
        run += p
        if i >= period:
            run -= prices[i - period]
        if i >= period - 1:
            out[i] = run / period
    return out


def ema(prices: list[float], period: int) -> list[float | None]:
    """Exponential Moving Average. Seed = SMA der ersten `period` Werte."""
    out: list[float | None] = [None] * len(prices)
    if period <= 0 or len(prices) < period:
        return out
    k = 2.0 / (period + 1)
    prev = sum(prices[:period]) / period
    out[period - 1] = prev
    for i in range(period, len(prices)):
        prev = prices[i] * k + prev * (1 - k)
        out[i] = prev
    return out


def rsi(prices: list[float], period: int = 14) -> list[float | None]:
    """Relative Strength Index nach Wilder's Smoothing. 0–100."""
    n = len(prices)
    out: list[float | None] = [None] * n
    if n <= period:
        return out

    gains = 0.0
    losses = 0.0
    for i in range(1, period + 1):
        change = prices[i] - prices[i - 1]
        gains += max(change, 0.0)
        losses += max(-change, 0.0)
    avg_gain = gains / period
    avg_loss = losses / period
    out[period] = _rsi_value(avg_gain, avg_loss)

    for i in range(period + 1, n):
        change = prices[i] - prices[i - 1]
        gain = max(change, 0.0)
        loss = max(-change, 0.0)
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        out[i] = _rsi_value(avg_gain, avg_loss)
    return out


def _rsi_value(avg_gain: float, avg_loss: float) -> float:
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def macd(
    prices: list[float], fast: int = 12, slow: int = 26, signal: int = 9
) -> dict[str, list[float | None]]:
    """MACD-Linie (EMA_fast - EMA_slow), Signal-Linie (EMA der MACD) und Histogramm."""
    ema_fast = ema(prices, fast)
    ema_slow = ema(prices, slow)
    macd_line: list[float | None] = [
        (f - s) if (f is not None and s is not None) else None
        for f, s in zip(ema_fast, ema_slow)
    ]

    # Signal-EMA nur über den zusammenhängenden, definierten MACD-Abschnitt.
    defined = [v for v in macd_line if v is not None]
    signal_tail = ema(defined, signal) if defined else []
    signal_line: list[float | None] = [None] * len(prices)
    first = next((i for i, v in enumerate(macd_line) if v is not None), None)
    if first is not None:
        for offset, val in enumerate(signal_tail):
            signal_line[first + offset] = val

    hist: list[float | None] = [
        (m - s) if (m is not None and s is not None) else None
        for m, s in zip(macd_line, signal_line)
    ]
    return {"macd": macd_line, "signal": signal_line, "histogram": hist}


def compute_all(prices: list[float]) -> dict:
    """Bündelt die gängigen Indikatoren für einen Chart-Abruf."""
    m = macd(prices)
    return {
        "sma20": sma(prices, 20),
        "sma50": sma(prices, 50),
        "ema12": ema(prices, 12),
        "ema26": ema(prices, 26),
        "rsi14": rsi(prices, 14),
        "macd": m["macd"],
        "macd_signal": m["signal"],
        "macd_histogram": m["histogram"],
    }
