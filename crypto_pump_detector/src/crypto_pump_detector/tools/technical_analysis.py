"""Technical analysis tool — Binance public API for OHLCV + indicator calculations."""

from __future__ import annotations

import time
from statistics import mean, stdev

import requests
from crewai.tools import tool

_BINANCE = "https://api.binance.com/api/v3"
_SESSION = requests.Session()
_last_call = 0.0


def _throttle(min_gap: float = 0.5) -> None:
    global _last_call
    elapsed = time.time() - _last_call
    if elapsed < min_gap:
        time.sleep(min_gap - elapsed)
    _last_call = time.time()


def _fetch_klines(symbol: str, interval: str, limit: int = 100) -> list[dict] | None:
    """Fetch OHLCV candlesticks from Binance."""
    _throttle()
    try:
        resp = _SESSION.get(
            f"{_BINANCE}/klines",
            params={"symbol": symbol, "interval": interval, "limit": limit},
            timeout=15,
        )
        if resp.status_code == 400:
            return None  # Symbol not on Binance
        resp.raise_for_status()
        raw = resp.json()
    except Exception:
        return None

    return [
        {
            "open_time": r[0],
            "open": float(r[1]),
            "high": float(r[2]),
            "low": float(r[3]),
            "close": float(r[4]),
            "volume": float(r[5]),
            "close_time": r[6],
        }
        for r in raw
    ]


def _rsi(closes: list[float], period: int = 14) -> float | None:
    """Calculate RSI (Relative Strength Index)."""
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i - 1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))

    avg_gain = mean(gains[:period])
    avg_loss = mean(losses[:period])

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)


def _ema(values: list[float], period: int) -> list[float]:
    """Calculate Exponential Moving Average."""
    if len(values) < period:
        return []
    multiplier = 2 / (period + 1)
    ema_vals = [mean(values[:period])]
    for v in values[period:]:
        ema_vals.append((v - ema_vals[-1]) * multiplier + ema_vals[-1])
    return ema_vals


def _macd(closes: list[float]) -> dict | None:
    """Calculate MACD (12, 26, 9)."""
    if len(closes) < 35:
        return None
    ema12 = _ema(closes, 12)
    ema26 = _ema(closes, 26)

    # Align lengths
    diff = len(ema12) - len(ema26)
    ema12 = ema12[diff:]

    macd_line = [a - b for a, b in zip(ema12, ema26)]
    if len(macd_line) < 9:
        return None
    signal_line = _ema(macd_line, 9)

    diff2 = len(macd_line) - len(signal_line)
    macd_line = macd_line[diff2:]

    histogram = [m - s for m, s in zip(macd_line, signal_line)]

    return {
        "macd": round(macd_line[-1], 6),
        "signal": round(signal_line[-1], 6),
        "histogram": round(histogram[-1], 6),
        "crossover": "BULLISH" if len(histogram) >= 2 and histogram[-2] < 0 and histogram[-1] > 0 else
                     "BEARISH" if len(histogram) >= 2 and histogram[-2] > 0 and histogram[-1] < 0 else
                     "NONE",
        "trend": "BULLISH" if histogram[-1] > 0 else "BEARISH",
    }


def _bollinger(closes: list[float], period: int = 20, num_std: float = 2.0) -> dict | None:
    """Calculate Bollinger Bands."""
    if len(closes) < period:
        return None
    recent = closes[-period:]
    sma = mean(recent)
    sd = stdev(recent)
    upper = sma + num_std * sd
    lower = sma - num_std * sd
    current = closes[-1]
    bandwidth = ((upper - lower) / sma) * 100 if sma else 0

    return {
        "upper": round(upper, 6),
        "middle": round(sma, 6),
        "lower": round(lower, 6),
        "bandwidth_pct": round(bandwidth, 2),
        "position": "ABOVE_UPPER" if current > upper else
                    "BELOW_LOWER" if current < lower else
                    "NEAR_UPPER" if current > sma + sd else
                    "NEAR_LOWER" if current < sma - sd else
                    "MIDDLE",
        "squeeze": bandwidth < 5,  # tight squeeze — breakout imminent
    }


def _volume_trend(klines: list[dict], lookback: int = 10) -> dict:
    """Analyze volume trend relative to recent history."""
    if len(klines) < lookback + 1:
        return {"trend": "UNKNOWN"}
    recent_vol = [k["volume"] for k in klines[-lookback:]]
    older_vol = [k["volume"] for k in klines[-(lookback * 2):-lookback]]
    if not older_vol:
        older_vol = recent_vol[:len(recent_vol) // 2] or [1]

    avg_recent = mean(recent_vol)
    avg_older = mean(older_vol) if older_vol else 1
    ratio = avg_recent / avg_older if avg_older else 1
    current_vs_avg = klines[-1]["volume"] / avg_recent if avg_recent else 1

    return {
        "recent_avg_volume": round(avg_recent, 2),
        "volume_increase_ratio": round(ratio, 2),
        "current_bar_vs_avg": round(current_vs_avg, 2),
        "trend": "SURGING" if ratio > 2.5 else
                 "INCREASING" if ratio > 1.5 else
                 "STABLE" if ratio > 0.7 else
                 "DECLINING",
        "current_bar_spike": current_vs_avg > 3.0,
    }


@tool("analyze_technicals")
def analyze_technicals(symbol: str) -> str:
    """Run full technical analysis on a crypto coin using Binance candlestick data.

    Calculates RSI, MACD (crossover detection), Bollinger Bands (squeeze detection),
    and volume trends on both 1h and 4h timeframes.

    Args:
        symbol: Trading pair symbol (e.g. 'BTCUSDT', 'SOLUSDT', 'PEPEUSDT').
                Append 'USDT' to the coin ticker. Use uppercase.
    """
    sym = symbol.upper().replace(" ", "")
    if not sym.endswith("USDT"):
        sym = sym + "USDT"

    results = []
    results.append(f"=== TECHNICAL ANALYSIS: {sym} ===\n")

    for interval, label in [("1h", "1-Hour"), ("4h", "4-Hour")]:
        klines = _fetch_klines(sym, interval, limit=100)
        if not klines:
            results.append(f"\n--- {label} Timeframe ---\nNo data available on Binance for {sym}.\n")
            continue

        closes = [k["close"] for k in klines]
        current_price = closes[-1]
        results.append(f"\n--- {label} Timeframe ({len(klines)} candles) ---")
        results.append(f"Current Price: ${current_price}")

        # RSI
        rsi_val = _rsi(closes)
        if rsi_val is not None:
            rsi_zone = (
                "OVERSOLD (buy opportunity)" if rsi_val < 30 else
                "OVERBOUGHT (caution)" if rsi_val > 70 else
                "STRONG MOMENTUM" if rsi_val > 55 else
                "NEUTRAL"
            )
            results.append(f"RSI(14): {rsi_val} — {rsi_zone}")

        # MACD
        macd_data = _macd(closes)
        if macd_data:
            results.append(
                f"MACD: {macd_data['macd']}  Signal: {macd_data['signal']}  "
                f"Histogram: {macd_data['histogram']}"
            )
            results.append(f"MACD Crossover: {macd_data['crossover']}  Trend: {macd_data['trend']}")

        # Bollinger Bands
        bb = _bollinger(closes)
        if bb:
            results.append(
                f"Bollinger Bands: Upper={bb['upper']}  Middle={bb['middle']}  "
                f"Lower={bb['lower']}"
            )
            results.append(
                f"BB Position: {bb['position']}  Bandwidth: {bb['bandwidth_pct']}%  "
                f"Squeeze: {'YES ⚡' if bb['squeeze'] else 'No'}"
            )

        # Volume
        vol = _volume_trend(klines)
        results.append(
            f"Volume Trend: {vol['trend']}  |  "
            f"Increase Ratio: {vol['volume_increase_ratio']}x  |  "
            f"Current Bar vs Avg: {vol['current_bar_vs_avg']}x"
        )
        if vol.get("current_bar_spike"):
            results.append("⚠️  CURRENT BAR VOLUME SPIKE DETECTED")

        # Support / Resistance (simple)
        highs = [k["high"] for k in klines[-20:]]
        lows = [k["low"] for k in klines[-20:]]
        results.append(
            f"20-bar Range: High=${max(highs):.6f}  Low=${min(lows):.6f}"
        )

    # Summary signals
    results.append("\n--- SIGNAL SUMMARY ---")
    # Re-check the 4h (preferred) or 1h data for final signal
    klines_4h = _fetch_klines(sym, "4h", limit=100)
    if klines_4h:
        closes = [k["close"] for k in klines_4h]
        signals = []
        rsi_val = _rsi(closes)
        if rsi_val and 45 < rsi_val < 70:
            signals.append(f"RSI in momentum zone ({rsi_val})")
        if rsi_val and rsi_val < 35:
            signals.append(f"RSI oversold — potential reversal ({rsi_val})")
        macd_data = _macd(closes)
        if macd_data and macd_data["crossover"] == "BULLISH":
            signals.append("MACD bullish crossover ✓")
        if macd_data and macd_data["trend"] == "BULLISH":
            signals.append("MACD bullish trend")
        bb = _bollinger(closes)
        if bb and bb["squeeze"]:
            signals.append("Bollinger squeeze — breakout imminent ✓")
        if bb and bb["position"] == "ABOVE_UPPER":
            signals.append("Price above Bollinger upper band — strong momentum ✓")
        vol = _volume_trend(klines_4h)
        if vol["trend"] in ("SURGING", "INCREASING"):
            signals.append(f"Volume {vol['trend'].lower()} ({vol['volume_increase_ratio']}x) ✓")

        if signals:
            results.append("Bullish signals found:")
            for s in signals:
                results.append(f"  ✓ {s}")
            results.append(f"Signal strength: {len(signals)}/6")
        else:
            results.append("No strong bullish signals on 4h timeframe.")

    return "\n".join(results)
