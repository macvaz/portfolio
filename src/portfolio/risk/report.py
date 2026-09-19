"""User-portfolio QuantStats reports and filesystem cache warm."""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

from portfolio.common.risk_report import (
    build_risk_report_html,
    portfolio_weights_are_complete,
)
from portfolio.common.risk_report_cache import (
    invalidate_portfolio_risk_reports,
    read_cached_risk_report,
    write_cached_risk_report,
)
from portfolio.storage.database import list_user_portfolio, list_users

logger = logging.getLogger(__name__)


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
    """Rebuild and store the full-period report for one portfolio.

    Skips generation when portfolio weights do not sum to ~100%, so partial
    allocations on the management screen do not trigger an automatic rebuild.
    """
    positions = list_user_portfolio(user_id, db_path)
    if not positions:
        invalidate_portfolio_risk_reports(user_id, reports_dir=reports_dir)
        return None

    if not portfolio_weights_are_complete(positions):
        logger.info(
            "Skipping risk report cache warm for portfolio %s: weights sum to %.4f",
            user_id,
            sum(float(position["weighted_assets"]) for position in positions),
        )
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
