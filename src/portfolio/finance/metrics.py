"""Fund performance metrics computed from stored NAV CSV files."""

from datetime import date
from pathlib import Path

import pandas as pd
import quantstats as qs

from portfolio.api.curve import (
    TRADING_DAYS_PER_YEAR,
    align_return_series,
    build_portfolio_daily_returns,
    load_benchmark_daily_returns,
)
from portfolio.api.database import list_funds, save_fund_metrics
from portfolio.finance.nav_files import load_fund_nav_csv

METRIC_KEYS = (
    "beta_6m",
    "cor_6m",
    "vol_1y",
    "pct_1w",
    "pct_2w",
    "pct_1m",
    "pct_3m",
    "pct_6m",
    "pct_ytd",
    "sr_6m",
    "sr_1y",
)

WINDOW_DAYS = {
    "1w": 5,
    "2w": 10,
    "1m": 21,
    "3m": 63,
    "6m": 126,
    "1y": TRADING_DAYS_PER_YEAR,
}


def _empty_metrics() -> dict[str, float | None]:
    return dict.fromkeys(METRIC_KEYS)


def _round_metric(value: float | None) -> float | None:
    if value is None or pd.isna(value):
        return None
    return round(float(value), 2)


def load_fund_daily_returns(
    isin: str,
    funds_dir: Path | None = None,
) -> pd.Series | None:
    """Daily simple returns for a fund from its stored NAV CSV."""
    nav_df = load_fund_nav_csv(isin, funds_dir)
    if nav_df.empty or "nav" not in nav_df.columns:
        return None

    returns = nav_df["nav"].pct_change().dropna()
    if returns.empty:
        return None

    returns.name = isin
    return returns


def _window_returns(returns: pd.Series, days: int) -> pd.Series:
    if returns.empty:
        return returns
    if len(returns) >= days:
        return returns.iloc[-days:]
    return returns


def _period_return_pct(returns: pd.Series) -> float | None:
    returns = returns.dropna()
    if returns.empty:
        return None
    total_return = (1 + returns).prod() - 1
    return _round_metric(total_return * 100)


def _ytd_return_pct(returns: pd.Series) -> float | None:
    if returns.empty:
        return None
    year_start = pd.Timestamp(date.today().year, 1, 1)
    ytd_returns = returns[returns.index >= year_start]
    return _period_return_pct(ytd_returns)


def compute_metrics(
    fund_returns: pd.Series,
    benchmark_returns: pd.Series | None = None,
) -> dict[str, float | None]:
    """Compute portfolio metrics from daily fund returns."""
    fund_returns = fund_returns.dropna()
    if fund_returns.empty:
        return _empty_metrics()

    metrics = _empty_metrics()
    metrics["pct_1w"] = _period_return_pct(
        _window_returns(fund_returns, WINDOW_DAYS["1w"])
    )
    metrics["pct_2w"] = _period_return_pct(
        _window_returns(fund_returns, WINDOW_DAYS["2w"])
    )
    metrics["pct_1m"] = _period_return_pct(
        _window_returns(fund_returns, WINDOW_DAYS["1m"])
    )
    metrics["pct_3m"] = _period_return_pct(
        _window_returns(fund_returns, WINDOW_DAYS["3m"])
    )
    metrics["pct_6m"] = _period_return_pct(
        _window_returns(fund_returns, WINDOW_DAYS["6m"])
    )
    metrics["pct_ytd"] = _ytd_return_pct(fund_returns)

    window_1y = _window_returns(fund_returns, WINDOW_DAYS["1y"])
    if len(window_1y) >= 2:
        vol = qs.stats.volatility(
            window_1y,
            periods=TRADING_DAYS_PER_YEAR,
            prepare_returns=False,
        )
        metrics["vol_1y"] = _round_metric(float(vol) * 100)

    window_6m = _window_returns(fund_returns, WINDOW_DAYS["6m"])
    if len(window_6m) >= 2:
        metrics["sr_6m"] = _round_metric(
            float(qs.stats.sharpe(window_6m, periods=TRADING_DAYS_PER_YEAR))
        )

    if len(window_1y) >= 2:
        metrics["sr_1y"] = _round_metric(
            float(qs.stats.sharpe(window_1y, periods=TRADING_DAYS_PER_YEAR))
        )

    if benchmark_returns is not None and not benchmark_returns.empty:
        fund_6m, benchmark_6m = align_return_series(
            _window_returns(fund_returns, WINDOW_DAYS["6m"]),
            _window_returns(benchmark_returns, WINDOW_DAYS["6m"]),
        )
        if fund_6m is not None and len(fund_6m) >= 2 and benchmark_6m is not None:
            greeks = qs.stats.greeks(fund_6m, benchmark_6m, prepare_returns=False)
            metrics["beta_6m"] = _round_metric(float(greeks["beta"]))
            metrics["cor_6m"] = _round_metric(float(fund_6m.corr(benchmark_6m)))

    return metrics


def compute_fund_metrics(
    isin: str,
    funds_dir: Path | None = None,
) -> dict[str, float | None]:
    """Compute metrics for one fund from its NAV file."""
    fund_returns = load_fund_daily_returns(isin, funds_dir)
    if fund_returns is None:
        return _empty_metrics()

    benchmark_returns = load_benchmark_daily_returns(funds_dir)
    return compute_metrics(fund_returns, benchmark_returns)


def compute_portfolio_metrics(
    positions: list[dict],
    funds_dir: Path | None = None,
) -> dict[str, float | None]:
    """Compute metrics for a weighted portfolio from stored NAV files."""
    portfolio_returns = build_portfolio_daily_returns(positions, funds_dir)
    if portfolio_returns is None or portfolio_returns.empty:
        return _empty_metrics()

    benchmark_returns = load_benchmark_daily_returns(funds_dir)
    portfolio_returns, benchmark_returns = align_return_series(
        portfolio_returns,
        benchmark_returns,
    )
    return compute_metrics(portfolio_returns, benchmark_returns)


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
