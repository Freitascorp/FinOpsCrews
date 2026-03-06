# stock_analyzer

> **Domain:** FinOps / Equities | **Data Source:** Yahoo Finance via `yfinance` (free, no API key)

Screen any stock universe for momentum and value, run 12+ technical indicators on every shortlisted ticker, assess fundamentals with DCF fair-value estimation, forecast 30-day price targets with Monte Carlo confidence intervals, and produce a ranked investment report with BUY / HOLD / AVOID recommendations.

---

## Agents

| Agent | Role |
|-------|------|
| `market_screener` | Stock Market Screener — runs two factor screens (momentum rank + value rank) on the full ticker list, merges results (dual-factor stocks ranked highest), pulls analyst targets and insider activity via `get_stock_info` |
| `chart_analyst` | Technical Chart Analyst — calls `analyze_chart` for every shortlisted ticker; documents 12+ indicators across trend, momentum, volatility, and volume dimensions; requires 3+ signal confluence before calling a setup valid |
| `fundamental_analyst` | Fundamental Equity Analyst — calls `analyze_fundamentals` per ticker; calculates DCF-inspired fair value, scores profitability (ROE, margins), growth (revenue CAGR), and financial safety (D/E, FCF yield) |
| `forecast_modeler` | Quantitative Price Forecaster — runs three independent models per ticker (linear regression, Monte Carlo 1000-path GBM, Holt exponential smoothing); reports upside probability, downside risk, volatility-adjusted price targets, and optimal stop-loss |
| `investment_strategist` | Chief Investment Strategist — synthesises all four outputs into a final ranked report with conviction tier, position sizing guidance, risk/reward ratio, and portfolio construction notes |

## Tasks

| Task | Output |
|------|--------|
| `screen_universe` | Ranked shortlist of 8–15 stocks with P/E, momentum, revenue growth, analyst target, and one-line thesis; ends with `SHORTLIST: AAPL,MSFT,...` for downstream parsing |
| `analyze_charts` | Technical summary per ticker: all indicator values, bullish/bearish signal count, support/resistance levels, entry zone, STRONGLY BULLISH → STRONGLY BEARISH verdict |
| `analyze_financials` | Fundamental summary per ticker: score (X/10), DCF fair value, upside/downside %, key strengths and risks, EXCELLENT/GOOD/FAIR/WEAK/POOR rating |
| `forecast_prices` | Price forecast per ticker: 3-model consensus target, confidence interval (1σ/2σ), upside probability, stop-loss level, scenario table (bull/base/bear) |
| `synthesise_recommendations` | Final investment report: conviction rankings (HIGH/MEDIUM/SPECULATIVE), BUY/HOLD/AVOID per ticker, portfolio allocation notes, risk factors, and overall market context |

## Inputs

| Input | Description | Default |
|-------|-------------|----------|
| `tickers` | Comma-separated stock tickers | 26-ticker diversified universe (Tech, Financials, Healthcare, Consumer, Energy, Industrials, Communications) |
| `sector` | Filter to a specific sector | `""` (all sectors) |
| `min_market_cap` | Minimum market cap filter (USD) | `1000000000` ($1B) |
| `analysis_period` | Historical data period | `6mo` |
| `forecast_days` | Days ahead to forecast | `30` |

## Tools

- `screen_stocks` — Yahoo Finance multi-factor stock screener (momentum + value sorts)
- `get_stock_info` — full company profile, analyst consensus, insider transactions
- `analyze_chart` — 12+ technical indicators: SMA/EMA, RSI, MACD, Bollinger, Stochastic, Fibonacci, OBV, VWAP, support/resistance
- `analyze_fundamentals` — valuation multiples, growth metrics, balance sheet, DCF fair value
- `forecast_price` — linear regression + Monte Carlo (1000 paths) + Holt-Winters smoothing

## Usage

```bash
cd stock_analyzer
crewai install   # or: uv sync
crewai run
```

### Custom inputs

```python
# src/stock_analyzer/main.py
StockAnalyzerCrew().crew().kickoff(inputs={
    "tickers": "AAPL,MSFT,GOOGL,NVDA,TSLA",
    "sector": "Technology",
    "min_market_cap": "10000000000",  # $10B+ large-caps only
    "analysis_period": "1y",
    "forecast_days": "60",
})
```

## Technical Indicators Reference

| Category | Indicators |
|----------|------------|
| Trend | SMA (20/50/200), EMA (12/26), Golden/Death Cross detection |
| Momentum | RSI (14), MACD (12/26/9) with crossover detection, Stochastic Oscillator |
| Volatility | Bollinger Bands (20, 2σ) with squeeze detection, ATR (14) |
| Volume | OBV, VWAP, relative volume trend |
| Patterns | Fibonacci retracements (23.6%, 38.2%, 50%, 61.8%, 78.6%), auto-detected support/resistance |

## ⚠️ Disclaimer

This crew provides data-driven analysis for informational purposes only — not financial advice. Past performance does not guarantee future results. Monte Carlo forecasts are probabilistic, not deterministic. Always do your own research before making investment decisions.

## Agents

| Agent | Role | Tools |
|-------|------|-------|
| **Market Screener** | Scans stock universe for momentum + value setups | `screen_stocks`, `get_stock_info` |
| **Chart Analyst** | Deep technical analysis with 12+ indicators | `analyze_chart` |
| **Fundamental Analyst** | Valuation, earnings, growth, financial health | `analyze_fundamentals` |
| **Forecast Modeler** | Statistical price forecasting with confidence intervals | `forecast_price` |
| **Investment Strategist** | Aggregates all signals into final recommendations | *(synthesises)* |

## Technical Indicators

- **Trend**: SMA (20/50/200), EMA (12/26), Golden/Death Cross detection
- **Momentum**: RSI (14), MACD (12/26/9) with crossover detection, Stochastic Oscillator
- **Volatility**: Bollinger Bands (20,2σ) with squeeze detection, ATR (14)
- **Volume**: OBV, VWAP, volume trend analysis
- **Patterns**: Fibonacci retracement levels (23.6%, 38.2%, 50%, 61.8%, 78.6%)
- **Support/Resistance**: Auto-detected from recent highs/lows

## Fundamental Metrics

- P/E, Forward P/E, PEG ratio, P/B, P/S
- Revenue & earnings growth (YoY, QoQ)
- Profit margins (gross, operating, net)
- Debt ratios (D/E, current ratio, quick ratio)
- Free cash flow yield, dividend yield
- Analyst targets & recommendations
- Insider transactions summary

## Forecasting

- Linear regression trendline with R² confidence
- Monte Carlo simulation (1000 paths, 30-day horizon)
- Exponential smoothing (Holt-Winters)
- Volatility-adjusted price targets (1σ, 2σ bands)
- Historical pattern matching (seasonal decomposition)

## Inputs

| Input | Default | Description |
|-------|---------|-------------|
| `tickers` | `AAPL,MSFT,GOOGL,AMZN,NVDA,TSLA,META,JPM,V,JNJ` | Comma-separated stock tickers |
| `sector` | *(empty)* | Filter by sector (e.g. `Technology`, `Healthcare`) |
| `min_market_cap` | `1000000000` | Minimum market cap ($1B default) |
| `analysis_period` | `6mo` | Historical data period (1mo, 3mo, 6mo, 1y, 2y) |
| `forecast_days` | `30` | Days to forecast ahead |

## Data Source

**Yahoo Finance** via `yfinance` — completely free, no API key required. Provides:
- Real-time & historical OHLCV data
- Fundamental data (balance sheet, income statement, cash flow)
- Analyst recommendations & price targets
- Insider transactions
- Options chain data

## Usage

```bash
cd examples/finops/stock_analyzer
crewai install
crewai run
```

Or via CrewHub triggers — schedule daily at market close for automated watchlist updates.

## Disclaimer

⚠️ This crew produces **algorithmic analysis, not financial advice**. Stock markets are inherently risky. Always do your own due diligence and consult a qualified financial advisor before making investment decisions. Past performance does not guarantee future results.
