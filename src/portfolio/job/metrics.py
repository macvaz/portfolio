"""Persist fund metrics computed from stored NAV files."""

from pathlib import Path

from portfolio.api.database import list_funds, save_fund_metrics
from portfolio.common.metrics import compute_fund_metrics


def refresh_fund_metrics(
    isin: str,
    db_path: Path | None = None,
    funds_dir: Path | None = None,
) -> dict[str, float | None]:
    """Recompute metrics from stored NAVs and persist them for one fund."""
    metrics = compute_fund_metrics(isin, funds_dir)
    save_fund_metrics(isin, metrics, db_path)
    return metrics


def update_all_fund_metrics(
    db_path: Path | None = None,
    funds_dir: Path | None = None,
) -> int:
    """Recompute and persist metrics for every fund in the database."""
    updated = 0
    for fund in list_funds(db_path):
        refresh_fund_metrics(fund["isin"], db_path, funds_dir)
        updated += 1
    return updated
