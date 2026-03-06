# crypto_pump_detector

> **Domain:** FinOps / Crypto | **Data Sources:** CoinGecko · Binance · DuckDuckGo (all free, no API keys)

Run three parallel market scans (general market, trending coins, meme/micro-caps), confirm breakout setups with technical indicators, layer on sentiment catalysts, and produce a ranked watchlist with entry zones, stop-loss levels, and conviction scores — before the big move happens.

---

## Agents

| Agent | Role |
|-------|------|
| `volume_scanner` | Crypto Volume & Momentum Scanner — runs three scan modes (general market movers, CoinGecko trending coins, meme-token category) to catch unusual volume spikes, BTC-decorrelated momentum, and ultra-low-cap meme tokens early |
| `technical_analyst` | Crypto Technical Analyst — calculates RSI, MACD crossover, Bollinger Band squeeze, and multi-timeframe (1h/4h) volume trends on Binance candlestick data to confirm or reject pump potential |
| `sentiment_scout` | Crypto Sentiment & Meme Scout — searches for exchange listing announcements, partnership news, whale wallet moves, influencer mentions, and viral meme catalysts; flags red flags (SEC, rug-pull, team dump) |
| `signal_aggregator` | Multi-Signal Investment Analyst — weights volume (25%), technicals (35%), sentiment (25%), and hype/trending (15%) into a composite score; separates meme/degen plays from higher-cap momentum plays with explicit risk ratings |

## Tasks

| Task | Output |
|------|--------|
| `scan_market` | Ranked list of 10–20 coins from all three scan modes, deduplicated, with pump score, scan source, and one-line flag reason |
| `analyze_candidates` | Technical summary per coin: RSI zone, MACD status, Bollinger position, volume trend, bullish signal count, BULLISH/NEUTRAL/BEARISH verdict |
| `gauge_sentiment` | Sentiment report per coin: rating (STRONGLY BEARISH → STRONGLY BULLISH), bullish/bearish keyword count, key headlines, catalysts, and red flags |
| `aggregate_signals` | Final ranked watchlist: composite score, entry zone, stop-loss, take-profit targets, risk tier (momentum play vs degen/meme), and ⚠️ risk disclaimer |

## Inputs

| Input | Description | Default |
|-------|-------------|----------|
| `min_market_cap` | Minimum market cap filter (USD) | `500000` ($500K) |
| `max_market_cap` | Maximum market cap filter (USD) | `5000000000` ($5B) |
| `volume_spike_threshold` | Volume/market-cap ratio threshold | `0.15` (15%) |
| `top_n` | Coins to return from general scan | `15` |

> Meme-coin scan always uses `min_market_cap=100000` regardless of the input setting.

## Tools

- `scan_market_movers` — CoinGecko market scan by volume/market-cap ratio
- `scan_trending_coins` — CoinGecko trending search leaderboard
- `scan_meme_coins` — CoinGecko meme-token category scan
- `get_coin_details` — full coin profile (ATH distance, supply, exchange presence, community)
- `analyze_technicals` — Binance OHLCV → RSI, MACD, Bollinger Bands, volume trend
- `search_crypto_sentiment` — DuckDuckGo news search for social catalysts and red flags

## Usage

```bash
cd crypto_pump_detector
crewai install   # or: uv sync
crewai run
```

### Custom inputs

```python
# src/crypto_pump_detector/main.py
CryptoPumpDetectorCrew().crew().kickoff(inputs={
    "min_market_cap": "100000",     # go lower for ultra micro-caps
    "max_market_cap": "500000000",  # cap at $500M for smaller plays
    "volume_spike_threshold": "0.20",
    "top_n": "20",
})
```

## Data Sources

| Source | Data | API Key |
|--------|------|---------|
| CoinGecko | Market cap, price changes (1h/24h/7d), trending, meme category | ❌ Not required |
| Binance | OHLCV candlesticks (1h, 4h) for technical analysis | ❌ Not required |
| DuckDuckGo | News and social sentiment search | ❌ Not required |

## ⚠️ Risk Disclaimer

Crypto markets are highly volatile. Pump-and-dump schemes are common in low-cap and meme tokens. This crew surfaces potential setups based on quantitative signals — it does not guarantee returns. Always use stop-losses and size positions appropriately. DYOR.

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
