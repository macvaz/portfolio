"""Filesystem cache for full-period QuantStats risk reports."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from portfolio.common.equity import BENCHMARK_ISIN
from portfolio.common.navs import DEFAULT_FUNDS_DIR, fund_nav_path

logger = logging.getLogger(__name__)

DEFAULT_RISK_REPORTS_DIR = Path("data/risk_reports")


def positions_fingerprint(positions: list[dict]) -> str:
    """Stable hash of portfolio weights (ISIN + weight)."""
    parts: list[str] = []
    for position in sorted(positions, key=lambda item: str(item["isin"]).upper()):
        isin = str(position["isin"]).upper()
        weight = float(position["weighted_assets"])
        parts.append(f"{isin}:{weight:.8f}")
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return digest[:16]


def nav_stamp(positions: list[dict], funds_dir: Path | None = None) -> str:
    """Max NAV file mtime among holdings + benchmark (nanoseconds)."""
    root = funds_dir or DEFAULT_FUNDS_DIR
    mtimes: list[int] = []
    isins = {str(position["isin"]).upper() for position in positions}
    isins.add(BENCHMARK_ISIN)
    for isin in isins:
        path = fund_nav_path(isin, root)
        if path.is_file():
            mtimes.append(path.stat().st_mtime_ns)
    return str(max(mtimes)) if mtimes else "0"


def risk_report_cache_path(
    portfolio_id: int,
    fingerprint: str,
    stamp: str,
    reports_dir: Path | None = None,
) -> Path:
    root = reports_dir or DEFAULT_RISK_REPORTS_DIR
    return root / f"{int(portfolio_id)}_{fingerprint}_{stamp}.html"


def invalidate_portfolio_risk_reports(
    portfolio_id: int,
    reports_dir: Path | None = None,
) -> None:
    """Remove cached full reports for one portfolio."""
    root = reports_dir or DEFAULT_RISK_REPORTS_DIR
    if not root.is_dir():
        return
    prefix = f"{int(portfolio_id)}_"
    for path in root.glob(f"{prefix}*.html"):
        try:
            path.unlink()
        except OSError:
            logger.warning("Could not remove stale risk report cache %s", path)


def invalidate_all_risk_reports(reports_dir: Path | None = None) -> None:
    """Remove all cached full reports."""
    root = reports_dir or DEFAULT_RISK_REPORTS_DIR
    if not root.is_dir():
        return
    for path in root.glob("*.html"):
        try:
            path.unlink()
        except OSError:
            logger.warning("Could not remove stale risk report cache %s", path)


def read_cached_risk_report(
    portfolio_id: int,
    positions: list[dict],
    funds_dir: Path | None = None,
    reports_dir: Path | None = None,
) -> str | None:
    """Return cached HTML when fingerprint + NAV stamp still match."""
    path = risk_report_cache_path(
        portfolio_id,
        positions_fingerprint(positions),
        nav_stamp(positions, funds_dir),
        reports_dir=reports_dir,
    )
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8")


def write_cached_risk_report(
    portfolio_id: int,
    positions: list[dict],
    html: str,
    funds_dir: Path | None = None,
    reports_dir: Path | None = None,
) -> Path:
    """Atomically store HTML and drop older cache files for this portfolio."""
    root = reports_dir or DEFAULT_RISK_REPORTS_DIR
    root.mkdir(parents=True, exist_ok=True)
    fingerprint = positions_fingerprint(positions)
    stamp = nav_stamp(positions, funds_dir)
    path = risk_report_cache_path(
        portfolio_id, fingerprint, stamp, reports_dir=root
    )
    tmp_path = path.with_suffix(".html.tmp")
    tmp_path.write_text(html, encoding="utf-8")
    tmp_path.replace(path)

    prefix = f"{int(portfolio_id)}_"
    for stale in root.glob(f"{prefix}*.html"):
        if stale != path:
            try:
                stale.unlink()
            except OSError:
                logger.warning("Could not remove stale risk report cache %s", stale)
    return path
