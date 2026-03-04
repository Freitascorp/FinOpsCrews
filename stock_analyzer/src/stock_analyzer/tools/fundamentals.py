"""Fundamental analysis tool — deep financial health and valuation analysis."""

from __future__ import annotations

# -- CrewHub compat: remove pyarrow stubs so yfinance uses pure pandas --
import sys as _sys
for _k in list(_sys.modules):
    if _k == "pyarrow" or _k.startswith("pyarrow."):
        del _sys.modules[_k]

import yfinance as yf
from crewai.tools import tool


def _fmt_num(val, suffix: str = "") -> str:
    """Format large numbers readably."""
    if val is None:
        return "N/A"
    if abs(val) >= 1e12:
        return f"${val/1e12:.2f}T{suffix}"
    if abs(val) >= 1e9:
        return f"${val/1e9:.2f}B{suffix}"
    if abs(val) >= 1e6:
        return f"${val/1e6:.1f}M{suffix}"
    return f"${val:,.0f}{suffix}"


def _pct(val) -> str:
    if val is None:
        return "N/A"
    return f"{val * 100:.2f}%"


def _safe(val, fmt: str = ".2f") -> str:
    if val is None:
        return "N/A"
    return f"{val:{fmt}}"


@tool("analyze_fundamentals")
def analyze_fundamentals(ticker: str) -> str:
    """Perform deep fundamental analysis on a stock.

    Analyzes financial statements, valuation metrics, growth trajectory,
    profitability, balance sheet health, cash flow, and computes a simple
    DCF-inspired fair value estimate.

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
        return f"ERROR: No data found for ticker '{sym}'."

    price = info.get("currentPrice") or info.get("regularMarketPrice") or 0
    mc = info.get("marketCap") or 0
    shares = info.get("sharesOutstanding") or 0

    out = [f"=== FUNDAMENTAL ANALYSIS: {info.get('shortName', sym)} ({sym}) ==="]
    out.append(f"Price: ${price:.2f}  |  Market Cap: {_fmt_num(mc)}")
    out.append(f"Sector: {info.get('sector', 'N/A')}  |  Industry: {info.get('industry', 'N/A')}\n")

    # ── Valuation Multiples ──
    out.append("--- VALUATION ---")
    pe = info.get("trailingPE")
    fwd_pe = info.get("forwardPE")
    peg = info.get("pegRatio")
    pb = info.get("priceToBook")
    ps = info.get("priceToSalesTrailing12Months")
    ev_ebitda = info.get("enterpriseToEbitda")

    out.append(f"Trailing P/E: {_safe(pe)}  |  Forward P/E: {_safe(fwd_pe)}")
    out.append(f"PEG Ratio: {_safe(peg)}  |  P/B: {_safe(pb)}  |  P/S: {_safe(ps)}")
    out.append(f"EV/EBITDA: {_safe(ev_ebitda)}")

    # Valuation assessment
    val_signals = []
    if pe and pe < 15:
        val_signals.append(f"Low P/E ({pe:.1f}) — potentially undervalued")
    elif pe and pe > 40:
        val_signals.append(f"High P/E ({pe:.1f}) — premium valuation")
    if peg and peg < 1:
        val_signals.append(f"PEG < 1 ({peg:.2f}) — growth at reasonable price ✓")
    if pb and pb < 1:
        val_signals.append(f"P/B < 1 ({pb:.2f}) — trading below book value ✓")
    if ev_ebitda and ev_ebitda < 10:
        val_signals.append(f"Low EV/EBITDA ({ev_ebitda:.1f}) — attractively valued ✓")

    if val_signals:
        out.append("Valuation Signals:")
        for s in val_signals:
            out.append(f"  → {s}")

    # ── Growth ──
    out.append("\n--- GROWTH ---")
    rev_growth = info.get("revenueGrowth")
    earn_growth = info.get("earningsGrowth")
    q_rev_growth = info.get("quarterlyRevenueGrowth")
    q_earn_growth = info.get("quarterlyEarningsGrowth")

    out.append(f"Revenue Growth (YoY): {_pct(rev_growth)}")
    out.append(f"Earnings Growth (YoY): {_pct(earn_growth)}")
    out.append(f"Q Rev Growth (QoQ): {_pct(q_rev_growth)}")
    out.append(f"Q Earn Growth (QoQ): {_pct(q_earn_growth)}")

    # Growth trajectory from financials
    try:
        inc = tk.income_stmt
        if inc is not None and not inc.empty and "Total Revenue" in inc.index:
            rev_row = inc.loc["Total Revenue"].dropna().sort_index()
            if len(rev_row) >= 2:
                revs = rev_row.tolist()
                out.append(f"\nRevenue History ({len(revs)} years):")
                for idx, val in zip(rev_row.index, revs):
                    yr = idx.year if hasattr(idx, "year") else str(idx)[:4]
                    out.append(f"  {yr}: {_fmt_num(val)}")
                if len(revs) >= 2 and revs[0] and revs[0] != 0:
                    cagr = ((revs[-1] / revs[0]) ** (1 / (len(revs) - 1)) - 1) * 100
                    out.append(f"Revenue CAGR: {cagr:.1f}%")
    except Exception:
        pass

    # ── Profitability ──
    out.append("\n--- PROFITABILITY ---")
    out.append(f"Gross Margin: {_pct(info.get('grossMargins'))}")
    out.append(f"Operating Margin: {_pct(info.get('operatingMargins'))}")
    out.append(f"Net Margin: {_pct(info.get('profitMargins'))}")
    out.append(f"ROE: {_pct(info.get('returnOnEquity'))}")
    out.append(f"ROA: {_pct(info.get('returnOnAssets'))}")

    roe = info.get("returnOnEquity")
    net_margin = info.get("profitMargins")
    prof_signals = []
    if roe and roe > 0.20:
        prof_signals.append(f"Excellent ROE ({roe*100:.1f}%) ✓")
    if net_margin and net_margin > 0.20:
        prof_signals.append(f"Strong net margin ({net_margin*100:.1f}%) ✓")
    elif net_margin and net_margin < 0:
        prof_signals.append(f"⚠️ Negative net margin ({net_margin*100:.1f}%)")
    if prof_signals:
        for s in prof_signals:
            out.append(f"  → {s}")

    # ── Balance Sheet ──
    out.append("\n--- FINANCIAL HEALTH ---")
    de = info.get("debtToEquity")
    cr = info.get("currentRatio")
    qr = info.get("quickRatio")
    out.append(f"Debt/Equity: {_safe(de)}")
    out.append(f"Current Ratio: {_safe(cr)}")
    out.append(f"Quick Ratio: {_safe(qr)}")

    total_cash = info.get("totalCash")
    total_debt = info.get("totalDebt")
    out.append(f"Cash on Hand: {_fmt_num(total_cash)}")
    out.append(f"Total Debt: {_fmt_num(total_debt)}")
    if total_cash and total_debt:
        net_cash = total_cash - total_debt
        out.append(f"Net Cash Position: {_fmt_num(net_cash)} {'✓' if net_cash > 0 else '⚠️'}")

    health_signals = []
    if de and de > 200:
        health_signals.append(f"⚠️ High leverage (D/E: {de:.0f})")
    elif de and de < 50:
        health_signals.append(f"Low debt (D/E: {de:.0f}) ✓")
    if cr and cr > 2:
        health_signals.append(f"Strong liquidity (CR: {cr:.2f}) ✓")
    elif cr and cr < 1:
        health_signals.append(f"⚠️ Weak liquidity (CR: {cr:.2f})")
    if health_signals:
        for s in health_signals:
            out.append(f"  → {s}")

    # ── Cash Flow ──
    out.append("\n--- CASH FLOW ---")
    fcf = info.get("freeCashflow")
    op_cf = info.get("operatingCashflow")
    out.append(f"Operating Cash Flow: {_fmt_num(op_cf)}")
    out.append(f"Free Cash Flow: {_fmt_num(fcf)}")
    if fcf and mc and mc > 0:
        fcf_yield = fcf / mc * 100
        out.append(f"FCF Yield: {fcf_yield:.2f}% {'✓ Attractive' if fcf_yield > 5 else ''}")

    # ── DCF-Inspired Fair Value Estimate ──
    out.append("\n--- FAIR VALUE ESTIMATE ---")
    if fcf and fcf > 0 and shares and shares > 0:
        # Simple DCF: 10-year projection at estimated growth rate, 10% discount
        growth = (rev_growth or 0.08)
        discount = 0.10
        terminal_growth = 0.025
        fcf_per_share = fcf / shares

        projected_fcfs = []
        running = fcf_per_share
        for yr in range(1, 11):
            g = growth * max(0.5, 1 - yr * 0.05)  # Growth decays over time
            running *= (1 + g)
            pv = running / ((1 + discount) ** yr)
            projected_fcfs.append(pv)

        terminal = running * (1 + terminal_growth) / (discount - terminal_growth)
        terminal_pv = terminal / ((1 + discount) ** 10)

        fair_value = sum(projected_fcfs) + terminal_pv
        upside = ((fair_value / price) - 1) * 100

        out.append(f"FCF/Share: ${fcf_per_share:.2f}")
        out.append(f"Assumed Growth: {growth*100:.1f}% (decaying)")
        out.append(f"Discount Rate: {discount*100:.0f}%")
        out.append(f"Estimated Fair Value: ${fair_value:.2f}")
        out.append(f"Current Price: ${price:.2f}")
        out.append(f"Upside/Downside: {upside:+.1f}%")
        if upside > 20:
            out.append("→ UNDERVALUED by DCF estimate ✓")
        elif upside < -20:
            out.append("→ OVERVALUED by DCF estimate ⚠️")
        else:
            out.append("→ FAIRLY VALUED")
    else:
        out.append("DCF not computable (negative or missing FCF)")

    # ── Dividend ──
    div_yield = info.get("dividendYield")
    if div_yield:
        out.append(f"\n--- DIVIDEND ---")
        out.append(f"Yield: {div_yield*100:.2f}%")
        out.append(f"Payout Ratio: {_pct(info.get('payoutRatio'))}")
        out.append(f"Ex-Dividend Date: {info.get('exDividendDate', 'N/A')}")

    # ── Analyst Consensus ──
    out.append(f"\n--- ANALYST CONSENSUS ---")
    out.append(f"Target Mean: ${info.get('targetMeanPrice', 'N/A')}")
    out.append(f"Target High: ${info.get('targetHighPrice', 'N/A')}")
    out.append(f"Target Low: ${info.get('targetLowPrice', 'N/A')}")
    out.append(f"Recommendation: {info.get('recommendationKey', 'N/A').upper()}")
    out.append(f"Number of Analysts: {info.get('numberOfAnalystOpinions', 'N/A')}")

    if info.get("targetMeanPrice") and price:
        analyst_upside = ((info["targetMeanPrice"] / price) - 1) * 100
        out.append(f"Analyst Upside: {analyst_upside:+.1f}%")

    # ── Overall Score ──
    out.append("\n--- FUNDAMENTAL SCORE ---")
    score = 0
    max_score = 0

    checks = [
        (pe and pe < 25, "Reasonable P/E"),
        (peg and peg < 1.5, "Growth at fair price (PEG)"),
        (roe and roe > 0.15, "Strong ROE"),
        (net_margin and net_margin > 0.10, "Good margins"),
        (de is not None and de < 100, "Manageable debt"),
        (cr and cr > 1.5, "Good liquidity"),
        (fcf and fcf > 0, "Positive free cash flow"),
        (rev_growth and rev_growth > 0.05, "Revenue growing"),
        (earn_growth and earn_growth > 0, "Earnings growing"),
        (div_yield and div_yield > 0.01, "Pays dividend"),
    ]
    for condition, label in checks:
        max_score += 1
        if condition:
            score += 1
            out.append(f"  ✓ {label}")
        else:
            out.append(f"  ✗ {label}")

    verdict = (
        "EXCELLENT" if score >= 8 else
        "GOOD" if score >= 6 else
        "FAIR" if score >= 4 else
        "WEAK" if score >= 2 else
        "POOR"
    )
    out.append(f"\nFundamental Score: {score}/{max_score} — {verdict}")

    return "\n".join(out)
