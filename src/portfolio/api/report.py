"""QuantStats risk analysis report for a saved user portfolio."""

from pathlib import Path

from portfolio import generate_performance_report_html
from portfolio.api.curve import (
    BENCHMARK_ISIN,
    build_portfolio_evolution,
    load_benchmark_daily_returns,
)
from portfolio.api.database import list_user_portfolio


def build_report_html(
    positions: list[dict],
    funds_dir: Path | None = None,
) -> str:
    """Build a QuantStats HTML tearsheet from stored NAV files."""
    evolution = build_portfolio_evolution(positions, funds_dir)
    if evolution is None or evolution.empty:
        raise ValueError("No NAV data available for the portfolio")

    portfolio_returns = evolution.pct_change().dropna()
    if portfolio_returns.empty:
        raise ValueError("No return data available for the portfolio")

    portfolio_returns.name = "Portfolio"

    benchmark_returns = load_benchmark_daily_returns(funds_dir)
    if benchmark_returns is None or benchmark_returns.empty:
        raise ValueError(f"No NAV data available for benchmark {BENCHMARK_ISIN}")

    return generate_performance_report_html(portfolio_returns, benchmark_returns)


def build_user_report_html(
    user_id: int,
    db_path=None,
    funds_dir: Path | None = None,
) -> str:
    positions = list_user_portfolio(user_id, db_path)
    if not positions:
        raise ValueError("Portfolio is empty")

    return build_report_html(positions, funds_dir)
