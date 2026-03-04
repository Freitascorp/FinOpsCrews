"""Crypto Pump Detector Crew — scan markets, analyse technicals, gauge sentiment, aggregate signals."""

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

from .tools import (
    analyze_technicals,
    get_coin_details,
    scan_market_movers,
    scan_meme_coins,
    scan_trending_coins,
    search_crypto_sentiment,
)


@CrewBase
class CryptoPumpDetectorCrew:
    """Crew that detects crypto coins showing early pump signals using live market data."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    # ── Agents ──────────────────────────────────────────────

    @agent
    def volume_scanner(self) -> Agent:
        return Agent(
            config=self.agents_config["volume_scanner"],
            tools=[scan_market_movers, scan_trending_coins, scan_meme_coins, get_coin_details],
            verbose=True,
        )

    @agent
    def technical_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config["technical_analyst"],
            tools=[analyze_technicals],
            verbose=True,
        )

    @agent
    def sentiment_scout(self) -> Agent:
        return Agent(
            config=self.agents_config["sentiment_scout"],
            tools=[search_crypto_sentiment],
            verbose=True,
        )

    @agent
    def signal_aggregator(self) -> Agent:
        return Agent(
            config=self.agents_config["signal_aggregator"],
            verbose=True,
        )

    # ── Tasks ───────────────────────────────────────────────

    @task
    def scan_market(self) -> Task:
        return Task(config=self.tasks_config["scan_market"])

    @task
    def analyze_candidates(self) -> Task:
        return Task(config=self.tasks_config["analyze_candidates"])

    @task
    def gauge_sentiment(self) -> Task:
        return Task(config=self.tasks_config["gauge_sentiment"])

    @task
    def aggregate_signals(self) -> Task:
        return Task(config=self.tasks_config["aggregate_signals"])

    # ── Crew ────────────────────────────────────────────────

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
