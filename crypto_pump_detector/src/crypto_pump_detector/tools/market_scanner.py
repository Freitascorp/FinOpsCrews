"""Market scanner tool — CoinGecko API for volume spikes and price momentum."""

from __future__ import annotations

import json
import time

import requests
from crewai.tools import tool

_COINGECKO = "https://api.coingecko.com/api/v3"
_SESSION = requests.Session()
_SESSION.headers.update({"Accept": "application/json"})

# Simple rate-limit helper (CoinGecko free tier: ~10-30 req/min)
_last_call = 0.0


def _throttle(min_gap: float = 2.5) -> None:
    global _last_call
    elapsed = time.time() - _last_call
    if elapsed < min_gap:
        time.sleep(min_gap - elapsed)
    _last_call = time.time()


def _score_coins(
    coins: list[dict],
    min_mc: float,
    max_mc: float,
    vol_thresh: float,
    btc_1h: float,
    btc_24h: float,
) -> list[dict]:
    """Score a list of CoinGecko market coins by pump potential."""
    signals: list[dict] = []
    for c in coins:
        mc = c.get("market_cap") or 0
        vol = c.get("total_volume") or 0
        if mc < min_mc or mc > max_mc or mc == 0:
            continue

        vol_ratio = vol / mc
        pct_1h = c.get("price_change_percentage_1h_in_currency") or 0
        pct_24h = c.get("price_change_percentage_24h_in_currency") or 0
        pct_7d = c.get("price_change_percentage_7d_in_currency") or 0

        # Pump score components
        vol_score = min(vol_ratio / vol_thresh, 3.0)  # 0-3
        momentum_1h = min(abs(pct_1h) / 5.0, 2.0) if pct_1h > 0 else 0  # 0-2
        momentum_24h = min(abs(pct_24h) / 15.0, 2.0) if pct_24h > 0 else 0  # 0-2

        # BTC decorrelation bonus
        decorr = 0.0
        if btc_1h > 0.1:
            decorr = min(abs(pct_1h) / (btc_1h * 3), 1.5)
        if btc_24h > 0.1:
            decorr = max(decorr, min(abs(pct_24h) / (btc_24h * 3), 1.5))

        # Reversal bonus — coin was down 7d but surging now
        reversal = 1.0 if pct_7d < -10 and pct_1h > 3 else 0.0

        pump_score = vol_score + momentum_1h + momentum_24h + decorr + reversal

        if pump_score >= 1.5 or vol_ratio >= vol_thresh:
            signals.append({
                "symbol": c.get("symbol", "?").upper(),
                "name": c.get("name", "?"),
                "id": c.get("id"),
                "price_usd": round(c.get("current_price") or 0, 8),
                "market_cap_m": round(mc / 1e6, 2),
                "volume_24h_m": round(vol / 1e6, 2),
                "vol_mcap_ratio": round(vol_ratio * 100, 2),
                "pct_1h": round(pct_1h, 2),
                "pct_24h": round(pct_24h, 2),
                "pct_7d": round(pct_7d, 2),
                "pump_score": round(pump_score, 2),
            })
    return signals


def _format_signals(signals: list[dict], header: str) -> str:
    """Format scored signals into readable output."""
    if not signals:
        return header + "No coins matched the pump-signal criteria.\n"
    rows = []
    for s in signals:
        rows.append(
            f"• {s['symbol']} ({s['name']}) — Score: {s['pump_score']}\n"
            f"  Price: ${s['price_usd']}  |  MCap: ${s['market_cap_m']}M  |  "
            f"Vol: ${s['volume_24h_m']}M  |  Vol/MCap: {s['vol_mcap_ratio']}%\n"
            f"  1h: {s['pct_1h']:+.2f}%  |  24h: {s['pct_24h']:+.2f}%  |  "
            f"7d: {s['pct_7d']:+.2f}%\n"
        )
    return header + "\n".join(rows)


@tool("scan_market_movers")
def scan_market_movers(
    min_market_cap: str = "500000",
    max_market_cap: str = "5000000000",
    volume_spike_threshold: str = "0.15",
    top_n: str = "25",
) -> str:
    """Scan the crypto market for coins showing unusual volume spikes and price
    momentum — early pump indicators.  Works for all coins including meme coins.

    Returns the top movers ranked by a composite pump-score based on:
    - Volume/market-cap ratio (normal 3-8%, spike > 15%)
    - 1-hour and 24-hour price change magnitude
    - Decorrelation from BTC (coins moving independently)
    - Reversal bonus (7d down but 1h surging — accumulation breakout)

    Args:
        min_market_cap: Minimum market cap in USD. Default 500K to catch micro-cap
                        meme coins.  Set to '1000000' for less noise.
        max_market_cap: Maximum market cap in USD (filters out mega-caps).
        volume_spike_threshold: Volume/market-cap ratio threshold (0.15 = 15%).
        top_n: Number of top movers to return.
    """
    min_mc = float(min_market_cap)
    max_mc = float(max_market_cap)
    vol_thresh = float(volume_spike_threshold)
    n = int(top_n)

    # Fetch market data — up to 250 coins per page
    coins: list[dict] = []
    for page in (1, 2):
        _throttle()
        try:
            resp = _SESSION.get(
                f"{_COINGECKO}/coins/markets",
                params={
                    "vs_currency": "usd",
                    "order": "volume_desc",
                    "per_page": 250,
                    "page": page,
                    "sparkline": "false",
                    "price_change_percentage": "1h,24h,7d",
                },
                timeout=30,
            )
            resp.raise_for_status()
            coins.extend(resp.json())
        except Exception as exc:
            if page == 1:
                return f"ERROR: Failed to fetch market data: {exc}"
            break

    # Get BTC reference for decorrelation check
    btc = next((c for c in coins if c.get("id") == "bitcoin"), None)
    btc_1h = abs(btc.get("price_change_percentage_1h_in_currency") or 0) if btc else 1
    btc_24h = abs(btc.get("price_change_percentage_24h_in_currency") or 0) if btc else 1

    signals = _score_coins(coins, min_mc, max_mc, vol_thresh, btc_1h, btc_24h)
    signals.sort(key=lambda x: x["pump_score"], reverse=True)
    signals = signals[:n]

    header = (
        f"Market scan complete — {len(signals)} coins flagged from {len(coins)} scanned.\n"
        f"BTC reference: 1h={btc_1h:.2f}%, 24h={btc_24h:.2f}%\n"
        f"Filters: market cap ${min_mc/1e6:.1f}M–${max_mc/1e6:.0f}M, "
        f"vol/mcap threshold {vol_thresh*100:.0f}%\n\n"
    )
    return _format_signals(signals, header)


def _resolve_coin_id(query: str) -> str | None:
    """Search CoinGecko for the correct coin ID when a direct lookup fails."""
    _throttle()
    try:
        resp = _SESSION.get(
            f"{_COINGECKO}/search",
            params={"query": query},
            timeout=15,
        )
        resp.raise_for_status()
        coins = resp.json().get("coins", [])
        if coins:
            return coins[0]["id"]  # Best match
    except Exception:
        pass
    return None


def _fetch_coin(coin_id: str) -> dict | str:
    """Fetch coin detail from CoinGecko, with search fallback on 404."""
    _throttle()
    try:
        resp = _SESSION.get(
            f"{_COINGECKO}/coins/{coin_id}",
            params={
                "localization": "false",
                "tickers": "true",
                "market_data": "true",
                "community_data": "true",
                "developer_data": "false",
                "sparkline": "false",
            },
            timeout=30,
        )
        if resp.status_code == 404:
            # Try resolving via search
            resolved = _resolve_coin_id(coin_id)
            if resolved and resolved != coin_id:
                return _fetch_coin(resolved)
            return f"ERROR: Coin '{coin_id}' not found on CoinGecko. Try the full slug (e.g. 'phala-network' instead of 'phala')."
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        return f"ERROR: Failed to fetch details for '{coin_id}': {exc}"


@tool("get_coin_details")
def get_coin_details(coin_id: str) -> str:
    """Get detailed market data for a specific coin from CoinGecko.

    Includes: current price, ATH, ATL, market cap rank, circulating vs total supply,
    24h high/low, community data, developer data, and tickers.

    Args:
        coin_id: CoinGecko coin ID or search term (e.g. 'bitcoin', 'solana', 'phala').
                 If the exact ID is not found, the tool automatically searches for the
                 closest match.
    """
    result = _fetch_coin(coin_id.lower().strip())
    if isinstance(result, str):
        return result  # Error message
    data = result

    md = data.get("market_data", {})
    usd = lambda d: d.get("usd", 0) if isinstance(d, dict) else 0

    # Top exchanges trading this coin
    tickers = data.get("tickers", [])[:5]
    exchange_info = ", ".join(
        f"{t.get('market', {}).get('name', '?')} ({t.get('base', '?')}/{t.get('target', '?')})"
        for t in tickers
    )

    community = data.get("community_data", {})

    return (
        f"=== {data.get('name', coin_id).upper()} ({data.get('symbol', '?').upper()}) ===\n"
        f"Market Cap Rank: #{data.get('market_cap_rank', '?')}\n"
        f"Price: ${usd(md.get('current_price'))}\n"
        f"24h High/Low: ${usd(md.get('high_24h'))} / ${usd(md.get('low_24h'))}\n"
        f"ATH: ${usd(md.get('ath'))} (change: {md.get('ath_change_percentage', {}).get('usd', 0):.1f}%)\n"
        f"ATL: ${usd(md.get('atl'))}\n"
        f"Market Cap: ${usd(md.get('market_cap'))/1e6:.1f}M\n"
        f"24h Volume: ${usd(md.get('total_volume'))/1e6:.1f}M\n"
        f"Circulating: {md.get('circulating_supply', 0):,.0f}\n"
        f"Total Supply: {md.get('total_supply') or 'unlimited'}\n"
        f"Max Supply: {md.get('max_supply') or 'no cap'}\n"
        f"Price Change 24h: {md.get('price_change_percentage_24h', 0):.2f}%\n"
        f"Price Change 7d: {md.get('price_change_percentage_7d', 0):.2f}%\n"
        f"Price Change 30d: {md.get('price_change_percentage_30d', 0):.2f}%\n"
        f"Top Exchanges: {exchange_info}\n"
        f"Twitter Followers: {community.get('twitter_followers', 'N/A')}\n"
        f"Reddit Subscribers: {community.get('reddit_subscribers', 'N/A')}\n"
        f"Description: {(data.get('description', {}).get('en', '') or '')[:300]}...\n"
    )


# ── NEW: Trending & Meme-coin scanners ───────────────────────────────


@tool("scan_trending_coins")
def scan_trending_coins() -> str:
    """Fetch the top trending coins on CoinGecko right now.

    CoinGecko's trending endpoint captures coins going viral based on
    search volume — this catches meme coins, new listings, and hype-driven
    pumps that volume scanners might miss because they haven't built up
    market cap yet.

    No arguments required.
    """
    _throttle()
    try:
        resp = _SESSION.get(f"{_COINGECKO}/search/trending", timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        return f"ERROR: Failed to fetch trending coins: {exc}"

    trending = data.get("coins", [])
    if not trending:
        return "No trending coins data available."

    results = [f"=== TRENDING COINS ON COINGECKO ({len(trending)} coins) ===\n"]
    for i, item in enumerate(trending, 1):
        c = item.get("item", {})
        price_btc = c.get("price_btc", 0)
        mc_rank = c.get("market_cap_rank") or "unranked"
        score = c.get("score", "?")
        results.append(
            f"{i}. {c.get('name', '?')} ({c.get('symbol', '?').upper()})\n"
            f"   CoinGecko ID: {c.get('id', '?')}\n"
            f"   Market Cap Rank: #{mc_rank}  |  Trend Score: {score}\n"
            f"   Price (BTC): {price_btc:.10f}\n"
        )

    results.append(
        "\n💡 Trending coins are ranked by search volume. High-ranking low-cap\n"
        "coins are prime meme-pump candidates — verify with technicals & sentiment."
    )
    return "\n".join(results)


@tool("scan_meme_coins")
def scan_meme_coins(
    min_market_cap: str = "100000",
    max_market_cap: str = "2000000000",
    top_n: str = "20",
) -> str:
    """Scan the meme-token category specifically for pump signals.

    Fetches coins tagged as 'meme-token' on CoinGecko and scores them
    using the same pump-score algorithm (volume spike, momentum, BTC
    decorrelation, reversal).  Ideal for finding degen plays early.

    Args:
        min_market_cap: Minimum market cap in USD.  Default 100K to catch
                        micro-cap meme coins before they explode.
        max_market_cap: Maximum market cap in USD.
        top_n: Number of top meme movers to return.
    """
    min_mc = float(min_market_cap)
    max_mc = float(max_market_cap)
    n = int(top_n)

    # Fetch meme-token category from CoinGecko
    coins: list[dict] = []
    for page in (1, 2, 3):  # Meme coins can span many pages
        _throttle()
        try:
            resp = _SESSION.get(
                f"{_COINGECKO}/coins/markets",
                params={
                    "vs_currency": "usd",
                    "category": "meme-token",
                    "order": "volume_desc",
                    "per_page": 250,
                    "page": page,
                    "sparkline": "false",
                    "price_change_percentage": "1h,24h,7d",
                },
                timeout=30,
            )
            resp.raise_for_status()
            batch = resp.json()
            if not batch:
                break
            coins.extend(batch)
        except Exception as exc:
            if page == 1:
                return f"ERROR: Failed to fetch meme coins: {exc}"
            break

    if not coins:
        return "No meme-token data available from CoinGecko."

    # BTC reference
    _throttle()
    btc_1h, btc_24h = 1.0, 1.0
    try:
        resp = _SESSION.get(
            f"{_COINGECKO}/coins/markets",
            params={
                "vs_currency": "usd",
                "ids": "bitcoin",
                "price_change_percentage": "1h,24h",
            },
            timeout=15,
        )
        resp.raise_for_status()
        btc = resp.json()[0] if resp.json() else {}
        btc_1h = abs(btc.get("price_change_percentage_1h_in_currency") or 0) or 1
        btc_24h = abs(btc.get("price_change_percentage_24h_in_currency") or 0) or 1
    except Exception:
        pass

    signals = _score_coins(coins, min_mc, max_mc, 0.15, btc_1h, btc_24h)
    signals.sort(key=lambda x: x["pump_score"], reverse=True)
    signals = signals[:n]

    header = (
        f"🐸 MEME COIN SCAN — {len(signals)} meme coins flagged from {len(coins)} scanned.\n"
        f"BTC reference: 1h={btc_1h:.2f}%, 24h={btc_24h:.2f}%\n"
        f"Filters: market cap ${min_mc/1e6:.2f}M–${max_mc/1e6:.0f}M\n\n"
    )
    return _format_signals(signals, header)
