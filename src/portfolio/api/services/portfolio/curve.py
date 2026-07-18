"""Real portfolio equity curve from stored NAV files."""

from datetime import date
from pathlib import Path

import pandas as pd

from portfolio.storage.database import list_user_portfolio
from portfolio.common.equity import (
    BENCHMARK_ISIN,
    BENCHMARK_NAME,
    TRADING_DAYS_PER_YEAR,
    align_return_series,
    build_portfolio_daily_returns,
    load_benchmark_daily_returns,
)

__all__ = [
    "BENCHMARK_ISIN",
    "BENCHMARK_NAME",
    "TRADING_DAYS_PER_YEAR",
    "align_return_series",
    "annualized_return_pct",
    "build_equity_curve",
    "build_portfolio_daily_returns",
    "build_user_equity_curve",
    "load_benchmark_daily_returns",
    "returns_to_cumulative_curve",
]


def _empty_curve() -> dict:
    return {
        "benchmark_name": BENCHMARK_NAME,
        "benchmark_isin": BENCHMARK_ISIN,
        "portfolio_annualized_pct": None,
        "benchmark_annualized_pct": None,
        "as_of": date.today().isoformat(),
        "labels": [],
        "portfolio": [],
        "benchmark": [],
    }


def returns_to_cumulative_curve(returns: pd.Series) -> tuple[list[str], list[float]]:
    """Convert daily simple returns to a cumulative % curve starting at zero."""
    returns = returns.dropna()
    if returns.empty:
        return [], []

    wealth = (1 + returns).cumprod()
    cumulative_pct = (wealth / wealth.iloc[0] - 1.0) * 100.0
    labels = [index_date.strftime("%Y-%m-%d") for index_date in cumulative_pct.index]
    values = [round(float(value), 2) for value in cumulative_pct.tolist()]
    return labels, values


def annualized_return_pct(
    returns: pd.Series,
    periods_per_year: int = TRADING_DAYS_PER_YEAR,
) -> float | None:
    """CAGR from daily returns, matching QuantStats (252 trading days per year)."""
    returns = returns.dropna()
    if returns.empty:
        return None

    total_return = (1 + returns).prod() - 1
    years = len(returns) / periods_per_year
    if years <= 0:
        return None

    annualized = (1 + total_return) ** (1 / years) - 1
    return round(float(annualized * 100), 2)


def build_equity_curve(
    positions: list[dict],
    funds_dir: Path | None = None,
) -> dict:
    """Compute buy-and-hold portfolio equity curve from local NAV CSV files."""
    portfolio_returns = build_portfolio_daily_returns(positions, funds_dir)
    if portfolio_returns is None or portfolio_returns.empty:
        return _empty_curve()

    benchmark_returns = load_benchmark_daily_returns(funds_dir)
    portfolio_returns, benchmark_returns = align_return_series(
        portfolio_returns,
        benchmark_returns,
    )

    labels, portfolio = returns_to_cumulative_curve(portfolio_returns)
    if not labels:
        return _empty_curve()

    benchmark: list[float] = []
    benchmark_annualized_pct = None
    if benchmark_returns is not None and not benchmark_returns.empty:
        _, benchmark = returns_to_cumulative_curve(benchmark_returns)
        benchmark_annualized_pct = annualized_return_pct(benchmark_returns)

    return {
        "benchmark_name": BENCHMARK_NAME,
        "benchmark_isin": BENCHMARK_ISIN,
        "portfolio_annualized_pct": annualized_return_pct(portfolio_returns),
        "benchmark_annualized_pct": benchmark_annualized_pct,
        "as_of": date.today().isoformat(),
        "labels": labels,
        "portfolio": portfolio,
        "benchmark": benchmark,
    }


def build_user_equity_curve(
    user_id: int,
    db_path=None,
    funds_dir: Path | None = None,
) -> dict:
    positions = list_user_portfolio(user_id, db_path)
    return build_equity_curve(positions, funds_dir)
