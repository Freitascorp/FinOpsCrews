"""Stock Analyzer Crew — screen, chart, value, forecast, and recommend."""

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

from .tools import (
    analyze_chart,
    analyze_fundamentals,
    forecast_price,
    get_stock_info,
    screen_stocks,
)


@CrewBase
class StockAnalyzerCrew:
    """Crew that performs deep stock analysis with charting, fundamentals, and forecasting."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    # ── Agents ──────────────────────────────────────────────

    @agent
    def market_screener(self) -> Agent:
        return Agent(
            config=self.agents_config["market_screener"],
            tools=[screen_stocks, get_stock_info],
            max_iter=40,
            verbose=True,
        )

    @agent
    def chart_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config["chart_analyst"],
            tools=[analyze_chart],
            max_iter=30,
            verbose=True,
        )

    @agent
    def fundamental_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config["fundamental_analyst"],
            tools=[analyze_fundamentals],
            max_iter=30,
            verbose=True,
        )

    @agent
    def forecast_modeler(self) -> Agent:
        return Agent(
            config=self.agents_config["forecast_modeler"],
            tools=[forecast_price],
            max_iter=30,
            verbose=True,
        )

    @agent
    def investment_strategist(self) -> Agent:
        return Agent(
            config=self.agents_config["investment_strategist"],
            verbose=True,
        )

    # ── Tasks ───────────────────────────────────────────────

    @task
    def screen_universe(self) -> Task:
        return Task(config=self.tasks_config["screen_universe"])

    @task
    def analyze_charts(self) -> Task:
        return Task(config=self.tasks_config["analyze_charts"])

    @task
    def analyze_financials(self) -> Task:
        return Task(config=self.tasks_config["analyze_financials"])

    @task
    def forecast_prices(self) -> Task:
        return Task(config=self.tasks_config["forecast_prices"])

    @task
    def synthesize_recommendations(self) -> Task:
        return Task(config=self.tasks_config["synthesize_recommendations"])

    # ── Crew ────────────────────────────────────────────────

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
