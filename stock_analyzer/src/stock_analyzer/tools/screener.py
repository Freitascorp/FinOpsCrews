"""Stock screener tool — Yahoo Finance for market scanning and stock info."""

from __future__ import annotations

# -- CrewHub compat: remove pyarrow stubs so yfinance uses pure pandas --
import sys as _sys
for _k in list(_sys.modules):
    if _k == "pyarrow" or _k.startswith("pyarrow."):
        del _sys.modules[_k]

import yfinance as yf
from crewai.tools import tool


@tool("screen_stocks")
def screen_stocks(
    tickers: str,
    min_market_cap: str = "1000000000",
    sort_by: str = "momentum",
) -> str:
    """Screen a list of stocks for investment opportunities.

    Fetches key metrics for each ticker and ranks them by the chosen criterion.
    Use this to narrow down a watchlist before deep analysis.

    Args:
        tickers: Comma-separated stock tickers (e.g. 'AAPL,MSFT,GOOGL,NVDA').
        min_market_cap: Minimum market cap in USD (default $1B).
        sort_by: Ranking criterion — 'momentum' (3mo return), 'value' (low P/E),
                 'growth' (revenue growth), or 'volume' (relative volume).
    """
    symbols = [t.strip().upper() for t in tickers.split(",") if t.strip()]
    min_mc = float(min_market_cap)

    results: list[dict] = []
    errors: list[str] = []

    for sym in symbols:
        try:
            tk = yf.Ticker(sym)
            info = tk.info or {}

            mc = info.get("marketCap") or 0
            if mc < min_mc:
                continue

            price = info.get("currentPrice") or info.get("regularMarketPrice") or 0
            pe = info.get("trailingPE") or info.get("forwardPE")
            fwd_pe = info.get("forwardPE")
            peg = info.get("pegRatio")
            pb = info.get("priceToBook")
            rev_growth = info.get("revenueGrowth")
            earn_growth = info.get("earningsGrowth")
            div_yield = info.get("dividendYield")
            beta = info.get("beta")
            avg_vol = info.get("averageVolume") or 1
            cur_vol = info.get("regularMarketVolume") or info.get("volume") or 0
            rel_vol = cur_vol / avg_vol if avg_vol else 0

            # Compute 3-month momentum
            hist = tk.history(period="3mo")
            if len(hist) >= 2:
                momentum_3m = ((hist["Close"].iloc[-1] / hist["Close"].iloc[0]) - 1) * 100
            else:
                momentum_3m = 0

            # 52-week position
            high_52 = info.get("fiftyTwoWeekHigh") or price
            low_52 = info.get("fiftyTwoWeekLow") or price
            range_pos = ((price - low_52) / (high_52 - low_52) * 100) if high_52 != low_52 else 50

            results.append({
                "symbol": sym,
                "name": info.get("shortName", sym),
                "price": round(price, 2),
                "market_cap_b": round(mc / 1e9, 2),
                "pe": round(pe, 2) if pe else None,
                "fwd_pe": round(fwd_pe, 2) if fwd_pe else None,
                "peg": round(peg, 2) if peg else None,
                "pb": round(pb, 2) if pb else None,
                "rev_growth_pct": round(rev_growth * 100, 1) if rev_growth else None,
                "earn_growth_pct": round(earn_growth * 100, 1) if earn_growth else None,
                "div_yield_pct": round(div_yield * 100, 2) if div_yield else None,
                "beta": round(beta, 2) if beta else None,
                "rel_volume": round(rel_vol, 2),
                "momentum_3m_pct": round(momentum_3m, 2),
                "range_52w_pct": round(range_pos, 1),
            })
        except Exception as exc:
            errors.append(f"{sym}: {exc}")

    if not results:
        msg = "No stocks matched the screening criteria."
        if errors:
            msg += f"\nErrors: {'; '.join(errors)}"
        return msg

    # Sort
    sort_key = {
        "momentum": lambda x: x["momentum_3m_pct"],
        "value": lambda x: -(x["pe"] or 9999),  # Lower P/E = better value
        "growth": lambda x: x["rev_growth_pct"] or 0,
        "volume": lambda x: x["rel_volume"],
    }.get(sort_by, lambda x: x["momentum_3m_pct"])

    results.sort(key=sort_key, reverse=True)

    header = f"=== STOCK SCREENER — {len(results)} stocks ranked by {sort_by} ===\n\n"
    rows = []
    for i, s in enumerate(results, 1):
        pe_str = f"P/E: {s['pe']}" if s["pe"] else "P/E: N/A"
        fwd_pe_str = f"Fwd P/E: {s['fwd_pe']}" if s["fwd_pe"] else ""
        peg_str = f"PEG: {s['peg']}" if s["peg"] else ""
        growth_str = f"Rev Growth: {s['rev_growth_pct']}%" if s["rev_growth_pct"] is not None else ""
        div_str = f"Div: {s['div_yield_pct']}%" if s["div_yield_pct"] else ""

        rows.append(
            f"{i}. {s['symbol']} ({s['name']}) — ${s['price']}\n"
            f"   MCap: ${s['market_cap_b']}B  |  {pe_str}  {fwd_pe_str}  {peg_str}\n"
            f"   3M Momentum: {s['momentum_3m_pct']:+.2f}%  |  52W Position: {s['range_52w_pct']}%\n"
            f"   {growth_str}  {div_str}  |  Rel Volume: {s['rel_volume']}x  Beta: {s['beta']}\n"
        )

    result = header + "\n".join(rows)
    if errors:
        result += f"\n\nSkipped ({len(errors)}): {'; '.join(errors)}"
    return result


@tool("get_stock_info")
def get_stock_info(ticker: str) -> str:
    """Get comprehensive stock information including company profile, key metrics,
    analyst recommendations, and insider activity.

    Args:
        ticker: Stock ticker symbol (e.g. 'AAPL', 'MSFT', 'NVDA').
    """
    sym = ticker.strip().upper()
    try:
        tk = yf.Ticker(sym)
        info = tk.info or {}
    except Exception as exc:
        return f"ERROR: Failed to fetch data for '{sym}': {exc}"

    if not info.get("shortName"):
        return f"ERROR: No data found for ticker '{sym}'. Check the symbol."

    price = info.get("currentPrice") or info.get("regularMarketPrice") or 0
    mc = info.get("marketCap") or 0

    # Analyst recommendations
    recs = ""
    try:
        rec_df = tk.recommendations
        if rec_df is not None and len(rec_df) > 0:
            recent = rec_df.tail(5)
            recs = "\n".join(
                f"  {r.get('period', '?')}: {r.get('strongBuy', 0)} Strong Buy, "
                f"{r.get('buy', 0)} Buy, {r.get('hold', 0)} Hold, "
                f"{r.get('sell', 0)} Sell, {r.get('strongSell', 0)} Strong Sell"
                for _, r in recent.iterrows()
            )
    except Exception:
        recs = "  Not available"

    # Insider transactions
    insider_str = ""
    try:
        insiders = tk.insider_transactions
        if insiders is not None and len(insiders) > 0:
            recent_ins = insiders.head(5)
            insider_str = "\n".join(
                f"  {r.get('Text', 'N/A')}"
                for _, r in recent_ins.iterrows()
            )
    except Exception:
        insider_str = "  Not available"

    # Build output
    return (
        f"=== {info.get('shortName', sym)} ({sym}) ===\n"
        f"Sector: {info.get('sector', 'N/A')}  |  Industry: {info.get('industry', 'N/A')}\n"
        f"Price: ${price}  |  Market Cap: ${mc/1e9:.2f}B\n"
        f"52W High: ${info.get('fiftyTwoWeekHigh', 'N/A')}  |  "
        f"52W Low: ${info.get('fiftyTwoWeekLow', 'N/A')}\n"
        f"\n--- Valuation ---\n"
        f"Trailing P/E: {info.get('trailingPE', 'N/A')}\n"
        f"Forward P/E: {info.get('forwardPE', 'N/A')}\n"
        f"PEG Ratio: {info.get('pegRatio', 'N/A')}\n"
        f"P/B: {info.get('priceToBook', 'N/A')}\n"
        f"P/S: {info.get('priceToSalesTrailing12Months', 'N/A')}\n"
        f"EV/EBITDA: {info.get('enterpriseToEbitda', 'N/A')}\n"
        f"\n--- Growth ---\n"
        f"Revenue Growth: {_pct(info.get('revenueGrowth'))}\n"
        f"Earnings Growth: {_pct(info.get('earningsGrowth'))}\n"
        f"Quarterly Revenue Growth: {_pct(info.get('quarterlyRevenueGrowth'))}\n"
        f"Quarterly Earnings Growth: {_pct(info.get('quarterlyEarningsGrowth'))}\n"
        f"\n--- Profitability ---\n"
        f"Gross Margin: {_pct(info.get('grossMargins'))}\n"
        f"Operating Margin: {_pct(info.get('operatingMargins'))}\n"
        f"Net Margin: {_pct(info.get('profitMargins'))}\n"
        f"ROE: {_pct(info.get('returnOnEquity'))}\n"
        f"ROA: {_pct(info.get('returnOnAssets'))}\n"
        f"\n--- Financial Health ---\n"
        f"Debt/Equity: {info.get('debtToEquity', 'N/A')}\n"
        f"Current Ratio: {info.get('currentRatio', 'N/A')}\n"
        f"Quick Ratio: {info.get('quickRatio', 'N/A')}\n"
        f"Free Cash Flow: ${(info.get('freeCashflow') or 0)/1e9:.2f}B\n"
        f"\n--- Dividend ---\n"
        f"Dividend Yield: {_pct(info.get('dividendYield'))}\n"
        f"Payout Ratio: {_pct(info.get('payoutRatio'))}\n"
        f"\n--- Analyst Targets ---\n"
        f"Target Mean: ${info.get('targetMeanPrice', 'N/A')}\n"
        f"Target High: ${info.get('targetHighPrice', 'N/A')}\n"
        f"Target Low: ${info.get('targetLowPrice', 'N/A')}\n"
        f"Recommendation: {info.get('recommendationKey', 'N/A')}\n"
        f"\n--- Recent Analyst Recommendations ---\n{recs}\n"
        f"\n--- Recent Insider Activity ---\n{insider_str}\n"
        f"\n--- Company ---\n"
        f"Employees: {info.get('fullTimeEmployees', 'N/A')}\n"
        f"Beta: {info.get('beta', 'N/A')}\n"
        f"Description: {(info.get('longBusinessSummary') or '')[:400]}...\n"
    )


def _pct(val) -> str:
    """Format a ratio as percentage string."""
    if val is None:
        return "N/A"
    return f"{val * 100:.2f}%"
