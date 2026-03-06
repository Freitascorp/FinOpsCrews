"""Sentiment analysis tool — DuckDuckGo search for crypto news & social buzz."""

from __future__ import annotations

import re
import time

from crewai.tools import tool

_last_call = 0.0


def _throttle(min_gap: float = 2.0) -> None:
    global _last_call
    elapsed = time.time() - _last_call
    if elapsed < min_gap:
        time.sleep(min_gap - elapsed)
    _last_call = time.time()


def _clean(text: str, max_len: int = 300) -> str:
    """Strip HTML tags and truncate."""
    clean = re.sub(r"<[^>]+>", "", text or "")
    return clean[:max_len]


@tool("search_crypto_sentiment")
def search_crypto_sentiment(coin_name: str) -> str:
    """Search the web for recent sentiment around a crypto coin.

    Looks for news articles, social media chatter, exchange listings,
    partnerships, whale movements, and pump/dump discussions.

    Args:
        coin_name: The name or ticker of the cryptocurrency (e.g. 'Solana', 'SOL',
                   'Pepe', 'BONK'). Use the common name for better results.
    """
    try:
        from ddgs import DDGS
    except ImportError:
        return "ERROR: ddgs package not installed. Run: pip install ddgs"

    queries = [
        f"{coin_name} crypto news today",
        f"{coin_name} crypto whale pump listing partnership",
    ]

    all_results = []
    seen_titles = set()

    ddgs = DDGS()

    for q in queries:
        _throttle()
        try:
            results = ddgs.text(q, region="en-us", max_results=8, timelimit="w")  # last week
        except Exception as exc:
            all_results.append(f"Search error for '{q}': {exc}")
            continue

        for r in results:
            title = r.get("title", "").strip()
            if title.lower() in seen_titles:
                continue
            seen_titles.add(title.lower())
            body = _clean(r.get("body", ""))
            href = r.get("href", "")
            all_results.append(f"• {title}\n  {body}\n  Link: {href}")

    if not all_results:
        return f"No recent sentiment data found for '{coin_name}'."

    # Quick sentiment heuristic
    bullish_words = [
        "surge", "rally", "pump", "moon", "breakout", "listing", "partnership",
        "bullish", "soar", "record", "adoption", "launch", "whale", "buy",
        "all-time high", "ath", "gains", "explode", "100x", "1000x", "fomo",
        "degen", "gem", "airdrop", "burn", "viral", "trending", "send it",
        "parabolic", "accumulation", "presale", "sold out", "elon",
        "memecoin", "meme coin", "to the moon", "lambo",
    ]
    bearish_words = [
        "crash", "dump", "scam", "rug", "bearish", "fraud", "hack", "exploit",
        "decline", "sell-off", "selloff", "plunge", "ban", "warning", "sec",
        "honeypot", "rugpull", "rug pull", "drain", "exit scam", "ponzi",
        "dead", "worthless", "fake", "avoid", "insider",
    ]

    full_text = " ".join(all_results).lower()
    bull_count = sum(1 for w in bullish_words if w in full_text)
    bear_count = sum(1 for w in bearish_words if w in full_text)

    if bull_count > bear_count + 2:
        sentiment = "STRONGLY BULLISH"
    elif bull_count > bear_count:
        sentiment = "LEANING BULLISH"
    elif bear_count > bull_count + 2:
        sentiment = "STRONGLY BEARISH"
    elif bear_count > bull_count:
        sentiment = "LEANING BEARISH"
    else:
        sentiment = "NEUTRAL / MIXED"

    header = (
        f"=== SENTIMENT ANALYSIS: {coin_name.upper()} ===\n"
        f"Overall Sentiment: {sentiment}\n"
        f"Bullish signals: {bull_count}  |  Bearish signals: {bear_count}\n"
        f"Articles found: {len(seen_titles)}\n"
        f"{'=' * 50}\n"
    )

    return header + "\n".join(all_results[:12])  # Cap at 12 results
