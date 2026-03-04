"""Chart analysis tool — deep technical analysis with 12+ indicators."""

from __future__ import annotations

# -- CrewHub compat: remove pyarrow stubs so yfinance uses pure pandas --
import sys as _sys
for _k in list(_sys.modules):
    if _k == "pyarrow" or _k.startswith("pyarrow."):
        del _sys.modules[_k]

from statistics import mean, stdev

import yfinance as yf
from crewai.tools import tool


# ── Indicator helpers ──────────────────────────────────────────────

def _sma(values: list[float], period: int) -> list[float]:
    """Simple Moving Average."""
    if len(values) < period:
        return []
    return [mean(values[i - period:i]) for i in range(period, len(values) + 1)]


def _ema(values: list[float], period: int) -> list[float]:
    """Exponential Moving Average."""
    if len(values) < period:
        return []
    mult = 2 / (period + 1)
    ema = [mean(values[:period])]
    for v in values[period:]:
        ema.append((v - ema[-1]) * mult + ema[-1])
    return ema


def _rsi(closes: list[float], period: int = 14) -> float | None:
    """RSI (Relative Strength Index)."""
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(closes)):
        d = closes[i] - closes[i - 1]
        gains.append(max(d, 0))
        losses.append(max(-d, 0))
    ag = mean(gains[:period])
    al = mean(losses[:period])
    for i in range(period, len(gains)):
        ag = (ag * (period - 1) + gains[i]) / period
        al = (al * (period - 1) + losses[i]) / period
    if al == 0:
        return 100.0
    return round(100 - (100 / (1 + ag / al)), 2)


def _macd(closes: list[float]) -> dict | None:
    """MACD (12, 26, 9)."""
    if len(closes) < 35:
        return None
    ema12 = _ema(closes, 12)
    ema26 = _ema(closes, 26)
    diff = len(ema12) - len(ema26)
    ema12 = ema12[diff:]
    macd_line = [a - b for a, b in zip(ema12, ema26)]
    if len(macd_line) < 9:
        return None
    signal = _ema(macd_line, 9)
    d2 = len(macd_line) - len(signal)
    macd_line = macd_line[d2:]
    hist = [m - s for m, s in zip(macd_line, signal)]
    crossover = "NONE"
    if len(hist) >= 2:
        if hist[-2] < 0 and hist[-1] > 0:
            crossover = "BULLISH"
        elif hist[-2] > 0 and hist[-1] < 0:
            crossover = "BEARISH"
    return {
        "macd": round(macd_line[-1], 4),
        "signal": round(signal[-1], 4),
        "histogram": round(hist[-1], 4),
        "crossover": crossover,
        "trend": "BULLISH" if hist[-1] > 0 else "BEARISH",
    }


def _bollinger(closes: list[float], period: int = 20, n_std: float = 2.0) -> dict | None:
    """Bollinger Bands."""
    if len(closes) < period:
        return None
    recent = closes[-period:]
    mid = mean(recent)
    sd = stdev(recent)
    upper = mid + n_std * sd
    lower = mid - n_std * sd
    bw = ((upper - lower) / mid * 100) if mid else 0
    cur = closes[-1]
    pos = (
        "ABOVE_UPPER" if cur > upper else
        "BELOW_LOWER" if cur < lower else
        "NEAR_UPPER" if cur > mid + sd else
        "NEAR_LOWER" if cur < mid - sd else
        "MIDDLE"
    )
    return {
        "upper": round(upper, 2), "middle": round(mid, 2), "lower": round(lower, 2),
        "bandwidth_pct": round(bw, 2), "position": pos, "squeeze": bw < 4,
    }


def _stochastic(highs: list[float], lows: list[float], closes: list[float],
                period: int = 14) -> dict | None:
    """%K and %D Stochastic Oscillator."""
    if len(closes) < period:
        return None
    h14 = max(highs[-period:])
    l14 = min(lows[-period:])
    if h14 == l14:
        return None
    k = ((closes[-1] - l14) / (h14 - l14)) * 100
    # %D = 3-period SMA of %K (approximate with single value)
    return {
        "k": round(k, 2),
        "zone": "OVERBOUGHT" if k > 80 else "OVERSOLD" if k < 20 else "NEUTRAL",
    }


def _atr(highs: list[float], lows: list[float], closes: list[float],
         period: int = 14) -> float | None:
    """Average True Range."""
    if len(closes) < period + 1:
        return None
    trs = []
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        trs.append(tr)
    return round(mean(trs[-period:]), 4)


def _obv(closes: list[float], volumes: list[float]) -> dict | None:
    """On-Balance Volume trend."""
    if len(closes) < 10:
        return None
    obv = 0
    obv_vals = []
    for i in range(1, len(closes)):
        if closes[i] > closes[i - 1]:
            obv += volumes[i]
        elif closes[i] < closes[i - 1]:
            obv -= volumes[i]
        obv_vals.append(obv)
    if len(obv_vals) < 10:
        return None
    recent_avg = mean(obv_vals[-5:])
    older_avg = mean(obv_vals[-10:-5])
    trend = "RISING" if recent_avg > older_avg * 1.05 else \
            "FALLING" if recent_avg < older_avg * 0.95 else "FLAT"
    return {"current_obv": round(obv_vals[-1]), "trend": trend}


def _fibonacci(high: float, low: float) -> dict:
    """Fibonacci retracement levels from recent high/low."""
    diff = high - low
    return {
        "high": round(high, 2),
        "low": round(low, 2),
        "23.6%": round(high - diff * 0.236, 2),
        "38.2%": round(high - diff * 0.382, 2),
        "50.0%": round(high - diff * 0.500, 2),
        "61.8%": round(high - diff * 0.618, 2),
        "78.6%": round(high - diff * 0.786, 2),
    }


def _detect_cross(short_ma: list[float], long_ma: list[float]) -> str:
    """Detect Golden Cross (bullish) or Death Cross (bearish)."""
    if len(short_ma) < 2 or len(long_ma) < 2:
        return "INSUFFICIENT DATA"
    # Align lengths
    mn = min(len(short_ma), len(long_ma))
    s = short_ma[-mn:]
    l = long_ma[-mn:]
    if s[-2] < l[-2] and s[-1] > l[-1]:
        return "GOLDEN CROSS ✓ (bullish — SMA50 crossed above SMA200)"
    elif s[-2] > l[-2] and s[-1] < l[-1]:
        return "DEATH CROSS ✗ (bearish — SMA50 crossed below SMA200)"
    elif s[-1] > l[-1]:
        return "BULLISH (SMA50 above SMA200)"
    else:
        return "BEARISH (SMA50 below SMA200)"


def _support_resistance(highs: list[float], lows: list[float], closes: list[float],
                         n: int = 3) -> dict:
    """Detect simple support/resistance levels from recent pivots."""
    resistances = sorted(set(round(h, 2) for h in highs[-30:]), reverse=True)[:n]
    supports = sorted(set(round(l, 2) for l in lows[-30:]))[:n]
    current = closes[-1]
    nearest_res = min(resistances, key=lambda x: abs(x - current)) if resistances else None
    nearest_sup = min(supports, key=lambda x: abs(x - current)) if supports else None
    return {
        "resistance_levels": resistances,
        "support_levels": supports,
        "nearest_resistance": nearest_res,
        "nearest_support": nearest_sup,
    }


def _volume_analysis(volumes: list[float], lookback: int = 20) -> dict:
    """Volume trend analysis."""
    if len(volumes) < lookback:
        return {"trend": "UNKNOWN"}
    recent = volumes[-lookback // 2:]
    older = volumes[-lookback:-lookback // 2]
    avg_r = mean(recent)
    avg_o = mean(older) or 1
    ratio = avg_r / avg_o
    cur_vs = volumes[-1] / avg_r if avg_r else 1
    return {
        "avg_volume": round(mean(volumes[-lookback:]), 0),
        "volume_ratio": round(ratio, 2),
        "current_vs_avg": round(cur_vs, 2),
        "trend": (
            "SURGING" if ratio > 2 else
            "INCREASING" if ratio > 1.3 else
            "STABLE" if ratio > 0.7 else
            "DECLINING"
        ),
        "spike": cur_vs > 2.5,
    }


# ── Main tool ──────────────────────────────────────────────────────


@tool("analyze_chart")
def analyze_chart(ticker: str, period: str = "6mo") -> str:
    """Perform comprehensive technical chart analysis on a stock.

    Calculates 12+ indicators across trend, momentum, volatility, and volume
    dimensions.  Includes Fibonacci retracement, support/resistance detection,
    and Golden/Death Cross analysis.

    Args:
        ticker: Stock ticker (e.g. 'AAPL', 'MSFT', 'NVDA').
        period: Data lookback period — '1mo', '3mo', '6mo', '1y', '2y'.
                Default '6mo'. Use '1y' for better moving average accuracy.
    """
    sym = ticker.strip().upper()
    try:
        tk = yf.Ticker(sym)
        hist = tk.history(period=period)
    except Exception as exc:
        return f"ERROR: Failed to fetch chart data for '{sym}': {exc}"

    if hist.empty or len(hist) < 30:
        return f"ERROR: Insufficient data for '{sym}' ({len(hist)} bars). Try a longer period."

    closes = hist["Close"].tolist()
    highs = hist["High"].tolist()
    lows = hist["Low"].tolist()
    volumes = hist["Volume"].tolist()
    current = closes[-1]

    out = [f"=== TECHNICAL CHART ANALYSIS: {sym} ==="]
    out.append(f"Period: {period}  |  Bars: {len(hist)}  |  Current Price: ${current:.2f}\n")

    # ── Moving Averages ──
    out.append("--- MOVING AVERAGES ---")
    sma20 = _sma(closes, 20)
    sma50 = _sma(closes, 50)
    sma200 = _sma(closes, 200)
    ema12 = _ema(closes, 12)
    ema26 = _ema(closes, 26)

    if sma20:
        out.append(f"SMA(20): ${sma20[-1]:.2f}  {'▲ Price above' if current > sma20[-1] else '▼ Price below'}")
    if sma50:
        out.append(f"SMA(50): ${sma50[-1]:.2f}  {'▲ Price above' if current > sma50[-1] else '▼ Price below'}")
    if sma200:
        out.append(f"SMA(200): ${sma200[-1]:.2f}  {'▲ Price above' if current > sma200[-1] else '▼ Price below'}")
    if ema12:
        out.append(f"EMA(12): ${ema12[-1]:.2f}  |  EMA(26): ${ema26[-1]:.2f}" if ema26 else f"EMA(12): ${ema12[-1]:.2f}")

    # Golden/Death Cross
    if sma50 and sma200:
        cross = _detect_cross(sma50, sma200)
        out.append(f"Cross Signal: {cross}")

    # Price vs MA alignment
    if sma20 and sma50:
        aligned = current > sma20[-1] > sma50[-1]
        if sma200:
            aligned = aligned and sma50[-1] > sma200[-1]
        out.append(f"MA Alignment: {'PERFECTLY BULLISH ✓' if aligned else 'NOT ALIGNED'}")

    # ── RSI ──
    out.append("\n--- MOMENTUM ---")
    rsi_val = _rsi(closes)
    if rsi_val is not None:
        zone = (
            "OVERSOLD (potential buy)" if rsi_val < 30 else
            "OVERBOUGHT (potential sell)" if rsi_val > 70 else
            "STRONG MOMENTUM" if rsi_val > 55 else
            "WEAK" if rsi_val < 45 else
            "NEUTRAL"
        )
        out.append(f"RSI(14): {rsi_val} — {zone}")

    # ── MACD ──
    macd_data = _macd(closes)
    if macd_data:
        out.append(
            f"MACD: {macd_data['macd']}  Signal: {macd_data['signal']}  "
            f"Hist: {macd_data['histogram']}"
        )
        out.append(f"MACD Crossover: {macd_data['crossover']}  |  Trend: {macd_data['trend']}")

    # ── Stochastic ──
    stoch = _stochastic(highs, lows, closes)
    if stoch:
        out.append(f"Stochastic %K(14): {stoch['k']} — {stoch['zone']}")

    # ── Bollinger Bands ──
    out.append("\n--- VOLATILITY ---")
    bb = _bollinger(closes)
    if bb:
        out.append(f"Bollinger: Upper=${bb['upper']}  Mid=${bb['middle']}  Lower=${bb['lower']}")
        out.append(f"BB Position: {bb['position']}  |  Bandwidth: {bb['bandwidth_pct']}%  |  Squeeze: {'YES ⚡' if bb['squeeze'] else 'No'}")

    # ── ATR ──
    atr_val = _atr(highs, lows, closes)
    if atr_val:
        atr_pct = (atr_val / current * 100)
        out.append(f"ATR(14): ${atr_val} ({atr_pct:.2f}% of price)")

    # ── Volume ──
    out.append("\n--- VOLUME ---")
    vol_data = _volume_analysis(volumes)
    out.append(f"Volume Trend: {vol_data['trend']}  |  Ratio: {vol_data.get('volume_ratio', '?')}x  |  Current vs Avg: {vol_data.get('current_vs_avg', '?')}x")
    if vol_data.get("spike"):
        out.append("⚠️  VOLUME SPIKE DETECTED")

    obv_data = _obv(closes, volumes)
    if obv_data:
        out.append(f"OBV Trend: {obv_data['trend']}")

    # ── Fibonacci ──
    out.append("\n--- FIBONACCI RETRACEMENT ---")
    high_range = max(highs[-60:]) if len(highs) >= 60 else max(highs)
    low_range = min(lows[-60:]) if len(lows) >= 60 else min(lows)
    fib = _fibonacci(high_range, low_range)
    for level, val in fib.items():
        marker = " ◀ CURRENT" if abs(current - val) / current < 0.01 else ""
        out.append(f"  {level}: ${val}{marker}")

    # ── Support / Resistance ──
    out.append("\n--- SUPPORT & RESISTANCE ---")
    sr = _support_resistance(highs, lows, closes)
    out.append(f"Resistance: {['$' + str(r) for r in sr['resistance_levels']]}")
    out.append(f"Support: {['$' + str(s) for s in sr['support_levels']]}")
    out.append(f"Nearest Resistance: ${sr['nearest_resistance']}  |  Nearest Support: ${sr['nearest_support']}")

    # ── Signal Summary ──
    out.append("\n--- SIGNAL SUMMARY ---")
    bull_signals = 0
    total_signals = 0

    if rsi_val:
        total_signals += 1
        if 40 < rsi_val < 70:
            bull_signals += 1
    if macd_data:
        total_signals += 1
        if macd_data["trend"] == "BULLISH":
            bull_signals += 1
        total_signals += 1
        if macd_data["crossover"] == "BULLISH":
            bull_signals += 1
    if bb:
        total_signals += 1
        if bb["squeeze"]:
            bull_signals += 1
        total_signals += 1
        if bb["position"] in ("ABOVE_UPPER", "NEAR_UPPER"):
            bull_signals += 1
    if stoch:
        total_signals += 1
        if stoch["zone"] != "OVERBOUGHT":
            bull_signals += 1
    if obv_data:
        total_signals += 1
        if obv_data["trend"] == "RISING":
            bull_signals += 1
    if vol_data.get("trend") in ("SURGING", "INCREASING"):
        total_signals += 1
        bull_signals += 1
    if sma50 and sma200 and sma50[-1] > sma200[-1]:
        total_signals += 1
        bull_signals += 1

    verdict = (
        "STRONGLY BULLISH" if bull_signals >= 7 else
        "BULLISH" if bull_signals >= 5 else
        "NEUTRAL" if bull_signals >= 3 else
        "BEARISH" if bull_signals >= 1 else
        "STRONGLY BEARISH"
    )
    out.append(f"Bullish Signals: {bull_signals}/{total_signals}")
    out.append(f"Technical Verdict: {verdict}")

    return "\n".join(out)
