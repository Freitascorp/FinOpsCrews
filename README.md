# FinOps Crews

A collection of **CrewAI crews** for financial market analysis — covering stock screening and crypto pump detection.

Each crew is a standalone CrewAI project with specialised agents, sequential task pipelines, and free data sources (no API keys required).

---

## Crews

| # | Directory | Name | Purpose |
|---|-----------|------|---------|
| 1 | `stock_analyzer/` | **Stock Analyzer** | Deep technical charting (12+ indicators), fundamental valuation, Monte Carlo forecasting, and investment recommendations across any stock universe |
| 2 | `crypto_pump_detector/` | **Crypto Pump Detector** | Scans 250+ coins for volume spikes, RSI/MACD breakouts, BTC decorrelation, and news catalysts to detect early pump signals |

---

## Quick Start

```bash
cd <crew_directory>
crewai install
crewai run
```

No API keys needed — both crews use free data sources:
- **Stock Analyzer** → Yahoo Finance via `yfinance`
- **Crypto Pump Detector** → CoinGecko + Binance + DuckDuckGo

---

## Chaining in CrewHub

These crews can be chained together in [CrewHub](https://github.com/Freitascorp/crewhub) using triggers.

### Crypto → Stocks cross-market scan

```
┌───────────────────────┐  on_success  ┌──────────────────┐
│ Crypto Pump Detector  │ ──────────► │ Stock Analyzer    │
│ (cron: every 4 hours) │              │ (scan crypto-     │
│                       │              │  correlated       │
│                       │              │  stocks: COIN,    │
│                       │              │  MSTR, MARA, etc) │
└───────────────────────┘              └──────────────────┘
```

### Daily market sweep

```
┌──────────────────┐         ┌───────────────────────┐
│ Stock Analyzer   │         │ Crypto Pump Detector   │
│ (cron: 9am ET    │         │ (cron: 9am ET          │
│  Mon-Fri)        │         │  daily)                │
└──────────────────┘         └───────────────────────┘
```

### Setup via CrewHub UI

1. **Add repo** → Repositories → Add `https://github.com/Freitascorp/FinOpsCrews` → Sync
2. **Create cron trigger** → Triggers → New → select crew, set cron expression
3. **Create chain trigger** → Triggers → New → type `on_success`, set source & target crew

---

## Project Structure

Each crew follows the standard CrewAI layout:

```
<crew_name>/
├── .env.example
├── README.md
├── pyproject.toml
└── src/<crew_name>/
    ├── __init__.py
    ├── crew.py
    ├── main.py
    ├── config/
    │   ├── agents.yaml
    │   └── tasks.yaml
    └── tools/
        ├── __init__.py
        └── *.py
```

## Disclaimer

These crews are for **educational and research purposes only**. Trading stocks and cryptocurrencies is risky. This is not financial advice. Never invest more than you can afford to lose.
