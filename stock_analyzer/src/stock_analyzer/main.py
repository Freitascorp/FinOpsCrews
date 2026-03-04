"""CLI entry point for stock_analyzer crew."""

from stock_analyzer.crew import StockAnalyzerCrew


def run():
    # Diversified universe spanning Tech, Financials, Healthcare, Consumer,
    # Energy, Industrials, and Communications for broad market coverage.
    tickers = ",".join([
        # Tech mega-caps
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA",
        # Financials
        "JPM", "V", "MA", "GS",
        # Healthcare
        "UNH", "JNJ", "LLY", "ABBV",
        # Consumer
        "WMT", "COST", "MCD", "NKE",
        # Energy
        "XOM", "CVX",
        # Industrials
        "CAT", "GE",
        # Communications & Entertainment
        "NFLX", "DIS",
    ])

    StockAnalyzerCrew().crew().kickoff(inputs={
        "tickers": tickers,
        "sector": "",
        "min_market_cap": "1000000000",
        "analysis_period": "6mo",
        "forecast_days": "30",
    })


if __name__ == "__main__":
    run()
