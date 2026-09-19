"""Persist fund metrics computed from stored NAV files."""

from pathlib import Path

from portfolio.storage.database import list_funds, save_fund_metrics
from portfolio.common.metrics import compute_fund_metrics


def refresh_fund_metrics(
    isin: str,
    db_path: Path | None = None,
    funds_dir: Path | None = None,
) -> dict[str, float | None]:
    """Recompute metrics from stored NAVs and persist them for one fund.

    When the NAV file is missing or yields no usable series, existing DB metrics
    are left unchanged (empty results are not written over good data).
    """
    metrics = compute_fund_metrics(isin, funds_dir)
    if all(value is None for value in metrics.values()):
        return metrics
    save_fund_metrics(isin, metrics, db_path)
    return metrics


def update_all_fund_metrics(
    db_path: Path | None = None,
    funds_dir: Path | None = None,
) -> int:
    """Recompute and persist metrics for every fund that has usable NAV data."""
    updated = 0
    for fund in list_funds(db_path):
        metrics = refresh_fund_metrics(fund["isin"], db_path, funds_dir)
        if any(value is not None for value in metrics.values()):
            updated += 1
    return updated
