"""Price forecasting tool — statistical models for price prediction."""

from __future__ import annotations

# -- CrewHub compat: remove pyarrow stubs so yfinance uses pure pandas --
import sys as _sys
for _k in list(_sys.modules):
    if _k == "pyarrow" or _k.startswith("pyarrow."):
        del _sys.modules[_k]

import random
from math import exp, log, sqrt
from statistics import mean, stdev

import yfinance as yf
from crewai.tools import tool


def _linear_regression(values: list[float]) -> dict:
    """Simple linear regression: y = mx + b. Returns slope, intercept, R²."""
    n = len(values)
    if n < 5:
        return {}
    x = list(range(n))
    x_mean = mean(x)
    y_mean = mean(values)
    ss_xy = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, values))
    ss_xx = sum((xi - x_mean) ** 2 for xi in x)
    ss_yy = sum((yi - y_mean) ** 2 for yi in values)
    if ss_xx == 0 or ss_yy == 0:
        return {}
    slope = ss_xy / ss_xx
    intercept = y_mean - slope * x_mean
    r_squared = (ss_xy ** 2) / (ss_xx * ss_yy)
    return {"slope": slope, "intercept": intercept, "r_squared": r_squared}


def _exponential_smoothing(values: list[float], alpha: float = 0.3,
                            beta: float = 0.1, horizon: int = 30) -> list[float]:
    """Double exponential smoothing (Holt's method) for trend forecasting."""
    if len(values) < 3:
        return []
    level = values[0]
    trend = values[1] - values[0]
    for v in values:
        new_level = alpha * v + (1 - alpha) * (level + trend)
        trend = beta * (new_level - level) + (1 - beta) * trend
        level = new_level
    forecasts = []
    for i in range(1, horizon + 1):
        forecasts.append(round(level + trend * i, 2))
    return forecasts


def _monte_carlo(closes: list[float], days: int = 30,
                  simulations: int = 1000) -> dict:
    """Monte Carlo simulation using geometric Brownian motion."""
    if len(closes) < 20:
        return {}

    # Calculate daily returns
    returns = [log(closes[i] / closes[i - 1]) for i in range(1, len(closes)) if closes[i - 1] > 0]
    if len(returns) < 10:
        return {}

    mu = mean(returns)
    sigma = stdev(returns)
    last_price = closes[-1]

    random.seed(42)  # Reproducible results

    final_prices = []
    paths: list[list[float]] = []

    for _ in range(simulations):
        price = last_price
        path = [price]
        for _ in range(days):
            daily_return = exp((mu - 0.5 * sigma ** 2) + sigma * random.gauss(0, 1))
            price *= daily_return
            path.append(round(price, 2))
        final_prices.append(price)
        if len(paths) < 5:  # Keep 5 sample paths
            paths.append(path)

    final_prices.sort()
    n = len(final_prices)

    return {
        "current_price": round(last_price, 2),
        "days": days,
        "simulations": simulations,
        "median": round(final_prices[n // 2], 2),
        "mean": round(mean(final_prices), 2),
        "p5": round(final_prices[int(n * 0.05)], 2),   # 5th percentile (bear case)
        "p25": round(final_prices[int(n * 0.25)], 2),  # 25th percentile
        "p75": round(final_prices[int(n * 0.75)], 2),  # 75th percentile
        "p95": round(final_prices[int(n * 0.95)], 2),  # 95th percentile (bull case)
        "prob_up": round(sum(1 for p in final_prices if p > last_price) / n * 100, 1),
        "prob_10pct_up": round(sum(1 for p in final_prices if p > last_price * 1.1) / n * 100, 1),
        "prob_10pct_down": round(sum(1 for p in final_prices if p < last_price * 0.9) / n * 100, 1),
        "daily_volatility": round(sigma * 100, 2),
        "annualized_volatility": round(sigma * sqrt(252) * 100, 2),
    }


def _seasonal_pattern(closes: list[float], period: int = 5) -> str:
    """Detect weekly seasonality pattern (5-day cycle)."""
    if len(closes) < period * 4:
        return "Insufficient data"
    # Average return by day-of-week position
    returns = [closes[i] / closes[i - 1] - 1 for i in range(1, len(closes))]
    day_returns: dict[int, list[float]] = {i: [] for i in range(period)}
    for i, r in enumerate(returns):
        day_returns[i % period].append(r)

    best_day = max(day_returns, key=lambda d: mean(day_returns[d]) if day_returns[d] else -999)
    worst_day = min(day_returns, key=lambda d: mean(day_returns[d]) if day_returns[d] else 999)
    day_names = {0: "Monday", 1: "Tuesday", 2: "Wednesday", 3: "Thursday", 4: "Friday"}

    return (
        f"Best avg day: {day_names.get(best_day, f'Day {best_day}')} "
        f"({mean(day_returns[best_day])*100:+.3f}%)  |  "
        f"Worst avg day: {day_names.get(worst_day, f'Day {worst_day}')} "
        f"({mean(day_returns[worst_day])*100:+.3f}%)"
    )


@tool("forecast_price")
def forecast_price(ticker: str, forecast_days: str = "30", period: str = "1y") -> str:
    """Forecast stock price using multiple statistical models.

    Runs three independent forecasting methods and combines them:
    1. Linear regression trendline with R² confidence
    2. Monte Carlo simulation (1000 paths, geometric Brownian motion)
    3. Exponential smoothing (Holt's double smoothing)

    Also provides volatility analysis, probability estimates, and
    historical seasonal patterns.

    Args:
        ticker: Stock ticker (e.g. 'AAPL', 'MSFT', 'NVDA').
        forecast_days: Number of trading days to forecast (default 30 ≈ 6 weeks).
        period: Historical data period for model training — '3mo', '6mo', '1y', '2y'.
    """
    sym = ticker.strip().upper()
    days = int(forecast_days)

    try:
        tk = yf.Ticker(sym)
        hist = tk.history(period=period)
    except Exception as exc:
        return f"ERROR: Failed to fetch data for '{sym}': {exc}"

    if hist.empty or len(hist) < 30:
        return f"ERROR: Insufficient data for '{sym}' ({len(hist)} bars)."

    closes = hist["Close"].tolist()
    current = closes[-1]

    out = [f"=== PRICE FORECAST: {sym} ==="]
    out.append(f"Current Price: ${current:.2f}  |  Data: {len(closes)} bars ({period})")
    out.append(f"Forecast Horizon: {days} trading days (~{days*7//5} calendar days)\n")

    # ── 1. Linear Regression ──
    out.append("--- MODEL 1: LINEAR REGRESSION ---")
    reg = _linear_regression(closes)
    if reg:
        trend_dir = "UPTREND" if reg["slope"] > 0 else "DOWNTREND"
        daily_change = reg["slope"]
        projected = reg["intercept"] + reg["slope"] * (len(closes) + days)
        pct_change = ((projected / current) - 1) * 100

        out.append(f"Trend: {trend_dir}  |  Daily slope: ${daily_change:.4f}")
        out.append(f"R² (fit quality): {reg['r_squared']:.4f} "
                   f"({'Strong' if reg['r_squared'] > 0.7 else 'Moderate' if reg['r_squared'] > 0.4 else 'Weak'} fit)")
        out.append(f"Projected Price ({days}d): ${projected:.2f} ({pct_change:+.1f}%)")

        # Confidence bands (±1σ, ±2σ)
        residuals = [c - (reg["intercept"] + reg["slope"] * i)
                     for i, c in enumerate(closes)]
        if len(residuals) > 2:
            res_std = stdev(residuals)
            out.append(f"1σ Band: ${projected - res_std:.2f} — ${projected + res_std:.2f}")
            out.append(f"2σ Band: ${projected - 2*res_std:.2f} — ${projected + 2*res_std:.2f}")

    # ── 2. Monte Carlo Simulation ──
    out.append("\n--- MODEL 2: MONTE CARLO SIMULATION ---")
    mc = _monte_carlo(closes, days)
    if mc:
        out.append(f"Simulations: {mc['simulations']}  |  Horizon: {mc['days']} days")
        out.append(f"Daily Volatility: {mc['daily_volatility']}%  |  "
                   f"Annualized: {mc['annualized_volatility']}%\n")
        out.append(f"  Bear Case (5th %%ile):  ${mc['p5']}  ({((mc['p5']/current)-1)*100:+.1f}%)")
        out.append(f"  Pessimistic (25th):     ${mc['p25']}  ({((mc['p25']/current)-1)*100:+.1f}%)")
        out.append(f"  Median (50th):          ${mc['median']}  ({((mc['median']/current)-1)*100:+.1f}%)")
        out.append(f"  Optimistic (75th):      ${mc['p75']}  ({((mc['p75']/current)-1)*100:+.1f}%)")
        out.append(f"  Bull Case (95th %%ile): ${mc['p95']}  ({((mc['p95']/current)-1)*100:+.1f}%)")
        out.append(f"\nProbability price goes UP: {mc['prob_up']}%")
        out.append(f"Probability +10% gain: {mc['prob_10pct_up']}%")
        out.append(f"Probability -10% loss: {mc['prob_10pct_down']}%")

    # ── 3. Exponential Smoothing ──
    out.append("\n--- MODEL 3: EXPONENTIAL SMOOTHING (HOLT) ---")
    es_forecasts = _exponential_smoothing(closes, horizon=days)
    if es_forecasts:
        es_final = es_forecasts[-1]
        es_mid = es_forecasts[days // 2] if days > 2 else es_final
        out.append(f"Midpoint ({days//2}d): ${es_mid:.2f} ({((es_mid/current)-1)*100:+.1f}%)")
        out.append(f"Endpoint ({days}d):  ${es_final:.2f} ({((es_final/current)-1)*100:+.1f}%)")
        out.append(f"Trend Direction: {'BULLISH ▲' if es_final > current else 'BEARISH ▼'}")

    # ── Seasonality ──
    out.append("\n--- SEASONAL PATTERNS ---")
    seasonal = _seasonal_pattern(closes)
    out.append(seasonal)

    # ── Consensus Forecast ──
    out.append("\n--- FORECAST CONSENSUS ---")
    forecasted_prices = []
    if reg:
        forecasted_prices.append(("Linear Regression", projected))
    if mc:
        forecasted_prices.append(("Monte Carlo (median)", mc["median"]))
    if es_forecasts:
        forecasted_prices.append(("Exponential Smoothing", es_final))

    if forecasted_prices:
        consensus_price = mean([p for _, p in forecasted_prices])
        consensus_pct = ((consensus_price / current) - 1) * 100

        out.append(f"{'Model':<30} {'Price':>10} {'Change':>10}")
        out.append("-" * 52)
        for name, price in forecasted_prices:
            pct = ((price / current) - 1) * 100
            out.append(f"{name:<30} ${price:>8.2f} {pct:>+9.1f}%")
        out.append("-" * 52)
        out.append(f"{'CONSENSUS'::<30} ${consensus_price:>8.2f} {consensus_pct:>+9.1f}%")

        direction = (
            "STRONGLY BULLISH" if consensus_pct > 10 else
            "BULLISH" if consensus_pct > 3 else
            "NEUTRAL" if consensus_pct > -3 else
            "BEARISH" if consensus_pct > -10 else
            "STRONGLY BEARISH"
        )
        out.append(f"\nForecast Direction: {direction}")

        # Risk-adjusted targets
        if mc:
            out.append(f"\n--- PRICE TARGETS ---")
            out.append(f"Conservative Target: ${mc['p25']:.2f}")
            out.append(f"Base Target: ${consensus_price:.2f}")
            out.append(f"Optimistic Target: ${mc['p75']:.2f}")
            out.append(f"Stop-Loss Suggestion: ${mc['p5']:.2f} (5th percentile)")

    out.append(f"\n⚠️ Statistical forecasts are based on historical patterns and do NOT")
    out.append(f"guarantee future results. Use as one input among many for decisions.")

    return "\n".join(out)
