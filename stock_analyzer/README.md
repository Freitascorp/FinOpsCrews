# Stock Analyzer Crew

AI-powered stock analysis crew that performs deep technical charting, fundamental valuation, and statistical price forecasting to surface excellent investment opportunities.

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
