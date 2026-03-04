# Crypto Pump Detector

AI-powered crew that monitors crypto markets in real-time to detect coins showing
early pump signals — **before** the big move happens.

## What It Does

1. **Volume Scanner** — Scans 250+ coins via CoinGecko for unusual volume spikes
   (volume/market-cap ratio), rapid price momentum (1h/24h), and coins with
   outsized moves relative to BTC.

2. **Technical Analyst** — Pulls Binance 1h and 4h candlestick data for flagged
   coins, calculates RSI, MACD, Bollinger Bands, and volume-weighted price trends
   to confirm breakout patterns.

3. **Sentiment Scout** — Searches DuckDuckGo for recent news, social buzz, and
   community chatter about flagged coins. Detects hype catalysts (listings,
   partnerships, burns, airdrops).

4. **Signal Aggregator** — Combines volume + technicals + sentiment into a ranked
   signal report with conviction scores, entry zones, stop-loss levels, and
   take-profit targets.

## Data Sources (All Free)

| Source | Data | API Key Required |
|--------|------|-----------------|
| CoinGecko | Market cap, volume, price changes (1h/24h/7d) for 250+ coins | No |
| Binance | OHLCV candlesticks (1h, 4h) for technical analysis | No |
| DuckDuckGo | News and social sentiment search | No |

## Detection Signals

- **Volume spike** — Volume/market-cap ratio > 15% (normal is 3-8%)
- **Price momentum** — 1h change > 5% or 24h change > 15%
- **BTC decorrelation** — Coin moving 3x+ more than BTC in the same period
- **RSI breakout** — RSI crossing above 55 from oversold territory
- **MACD crossover** — Bullish MACD cross on 4h timeframe
- **Bollinger squeeze** — Price breaking above upper band after tight squeeze
- **News catalyst** — Recent listings, partnerships, burns, or whale activity

## Output

A ranked markdown report with:
- Top coins showing pump signals (ranked by conviction score 1-10)
- Entry zone, stop-loss, and take-profit for each
- Risk assessment and timeframe estimate
- Supporting evidence (volume data, technicals, news links)

## Inputs

| Input | Description | Default |
|-------|------------|---------|
| `min_market_cap` | Minimum market cap filter (USD) | `10000000` (10M) |
| `max_market_cap` | Maximum market cap filter (USD) | `5000000000` (5B) |
| `volume_spike_threshold` | Volume/market-cap ratio threshold | `0.15` |
| `top_n` | Number of top signals to return | `10` |

## ⚠️ Disclaimer

This crew is for **educational and research purposes only**. Cryptocurrency
trading is extremely risky. Past pump patterns do not guarantee future results.
Never invest more than you can afford to lose. This is not financial advice.
