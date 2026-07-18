"""QuantStats risk report for a saved user portfolio."""

from pathlib import Path

from portfolio.api.services.portfolio.quantstats import generate_performance_report_html
from portfolio.common.equity import (
    BENCHMARK_ISIN,
    align_return_series,
    build_portfolio_daily_returns,
    load_benchmark_daily_returns,
)
from portfolio.storage.database import list_user_portfolio


def build_risk_report_html(
    positions: list[dict],
    funds_dir: Path | None = None,
) -> str:
    """Build a QuantStats HTML tearsheet from stored NAV files."""
    portfolio_returns = build_portfolio_daily_returns(positions, funds_dir)
    if portfolio_returns is None or portfolio_returns.empty:
        raise ValueError("No NAV data available for the portfolio")

    benchmark_returns = load_benchmark_daily_returns(funds_dir)
    if benchmark_returns is None or benchmark_returns.empty:
        raise ValueError(f"No NAV data available for benchmark {BENCHMARK_ISIN}")

    portfolio_returns, benchmark_returns = align_return_series(
        portfolio_returns,
        benchmark_returns,
    )
    if benchmark_returns is None or benchmark_returns.empty:
        raise ValueError(f"No NAV data available for benchmark {BENCHMARK_ISIN}")

    return generate_performance_report_html(portfolio_returns, benchmark_returns)


def build_user_risk_report_html(
    user_id: int,
    db_path=None,
    funds_dir: Path | None = None,
) -> str:
    positions = list_user_portfolio(user_id, db_path)
    if not positions:
        raise ValueError("Portfolio is empty")

    return build_risk_report_html(positions, funds_dir)
