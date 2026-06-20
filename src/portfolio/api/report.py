"""QuantStats risk analysis report for a saved user portfolio."""

from pathlib import Path

import pandas as pd

from portfolio import generate_performance_report_html
from portfolio.api.curve import build_portfolio_evolution
from portfolio.api.database import list_user_portfolio

DEFAULT_BENCHMARK = "SPY"


def build_report_html(
    positions: list[dict],
    benchmark: str = DEFAULT_BENCHMARK,
    funds_dir: Path | None = None,
) -> str:
    """Build a QuantStats HTML tearsheet from stored NAV files."""
    evolution = build_portfolio_evolution(positions, funds_dir)
    if evolution is None or evolution.empty:
        raise ValueError("No NAV data available for the portfolio")

    portfolio_df = pd.DataFrame({"portfolio": evolution})
    return generate_performance_report_html(portfolio_df, benchmark)


def build_user_report_html(
    user_id: int,
    benchmark: str = DEFAULT_BENCHMARK,
    db_path=None,
    funds_dir: Path | None = None,
) -> str:
    positions = list_user_portfolio(user_id, db_path)
    if not positions:
        raise ValueError("Portfolio is empty")

    return build_report_html(positions, benchmark, funds_dir)
