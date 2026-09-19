"""QuantStats risk report HTML from portfolio positions (no DB)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from portfolio.common.equity import (
    BENCHMARK_ISIN,
    align_return_series,
    build_portfolio_daily_returns,
    load_benchmark_daily_returns,
    slice_returns_from,
)
from portfolio.common.quantstats_report import generate_performance_report_html

# Same tolerance as portfolio position validation in management schemas.
WEIGHT_SUM_TOLERANCE = 0.01


def portfolio_weights_are_complete(positions: list[dict]) -> bool:
    """True when invested weights sum to ~100% (cash remainder is not allowed)."""
    if not positions:
        return False
    total = sum(float(position["weighted_assets"]) for position in positions)
    return abs(total - 1.0) <= WEIGHT_SUM_TOLERANCE


def build_risk_report_html(
    positions: list[dict],
    funds_dir: Path | None = None,
    start_date: date | None = None,
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
    portfolio_returns = slice_returns_from(portfolio_returns, start_date)
    benchmark_returns = slice_returns_from(benchmark_returns, start_date)

    if portfolio_returns is None or portfolio_returns.empty:
        raise ValueError("No NAV data available for the portfolio")
    if benchmark_returns is None or benchmark_returns.empty:
        raise ValueError(f"No NAV data available for benchmark {BENCHMARK_ISIN}")

    return generate_performance_report_html(portfolio_returns, benchmark_returns)
