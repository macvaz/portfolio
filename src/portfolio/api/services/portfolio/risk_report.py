"""QuantStats risk report for a saved user portfolio."""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

from portfolio.api.services.portfolio.quantstats import generate_performance_report_html
from portfolio.api.services.portfolio.risk_report_cache import (
    invalidate_portfolio_risk_reports,
    read_cached_risk_report,
    write_cached_risk_report,
)
from portfolio.common.equity import (
    BENCHMARK_ISIN,
    align_return_series,
    build_portfolio_daily_returns,
    load_benchmark_daily_returns,
    slice_returns_from,
)
from portfolio.storage.database import list_user_portfolio, list_users

logger = logging.getLogger(__name__)


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


def build_user_risk_report_html(
    user_id: int,
    db_path=None,
    funds_dir: Path | None = None,
    start_date: date | None = None,
    *,
    reports_dir: Path | None = None,
) -> str:
    """Return a tearsheet; cache only the full-period (no start_date) report."""
    positions = list_user_portfolio(user_id, db_path)
    if not positions:
        raise ValueError("Portfolio is empty")

    if start_date is not None:
        return build_risk_report_html(positions, funds_dir, start_date=start_date)

    cached = read_cached_risk_report(
        user_id, positions, funds_dir=funds_dir, reports_dir=reports_dir
    )
    if cached is not None:
        return cached

    html = build_risk_report_html(positions, funds_dir, start_date=None)
    write_cached_risk_report(
        user_id,
        positions,
        html,
        funds_dir=funds_dir,
        reports_dir=reports_dir,
    )
    return html


def warm_user_risk_report_cache(
    user_id: int,
    db_path=None,
    funds_dir: Path | None = None,
    reports_dir: Path | None = None,
) -> str | None:
    """Rebuild and store the full-period report for one portfolio."""
    positions = list_user_portfolio(user_id, db_path)
    if not positions:
        invalidate_portfolio_risk_reports(user_id, reports_dir=reports_dir)
        return None

    invalidate_portfolio_risk_reports(user_id, reports_dir=reports_dir)
    html = build_risk_report_html(positions, funds_dir, start_date=None)
    write_cached_risk_report(
        user_id,
        positions,
        html,
        funds_dir=funds_dir,
        reports_dir=reports_dir,
    )
    return html


def warm_all_risk_report_caches(
    db_path=None,
    funds_dir: Path | None = None,
    reports_dir: Path | None = None,
) -> int:
    """Warm full-period caches for every non-empty portfolio. Returns count warmed."""
    warmed = 0
    for user in list_users(db_path):
        user_id = int(user["id"])
        try:
            if warm_user_risk_report_cache(
                user_id,
                db_path=db_path,
                funds_dir=funds_dir,
                reports_dir=reports_dir,
            ):
                warmed += 1
                logger.info("Warmed risk report cache for portfolio %s", user_id)
        except Exception:
            logger.exception(
                "Failed to warm risk report cache for portfolio %s", user_id
            )
    return warmed
