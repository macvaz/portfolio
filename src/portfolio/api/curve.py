"""Real portfolio equity curve from stored NAV files."""

from datetime import date
from pathlib import Path

import pandas as pd

from portfolio.api.database import list_user_portfolio
from portfolio.finance.nav_files import load_fund_nav_csv
from portfolio.finance.returns import calculate_buy_and_hold_returns

BENCHMARK_NAME = "S&P 500"
BENCHMARK_ISIN = "IE00BYX5MX67"
CHART_BASE_VALUE = 100.0


def _empty_curve() -> dict:
    return {
        "benchmark_name": BENCHMARK_NAME,
        "as_of": date.today().isoformat(),
        "labels": [],
        "portfolio": [],
        "benchmark": [],
    }


def _portfolio_weights(positions: list[dict]) -> tuple[dict[str, float], float]:
    """Return fund weights and uninvested cash weight from saved positions."""
    weights = {
        position["isin"]: float(position["weighted_assets"])
        for position in positions
        if float(position["weighted_assets"]) > 0
    }
    total = sum(weights.values())
    if total <= 0:
        return {}, 0.0

    if total > 1.0:
        return {isin: weight / total for isin, weight in weights.items()}, 0.0

    return weights, 1.0 - total


def _load_portfolio_navs(
    weights: dict[str, float],
    funds_dir: Path | None = None,
) -> pd.DataFrame:
    series: dict[str, pd.Series] = {}
    for isin in weights:
        nav_df = load_fund_nav_csv(isin, funds_dir)
        if nav_df.empty or "nav" not in nav_df.columns:
            continue
        series[isin] = nav_df["nav"]

    if not series:
        return pd.DataFrame()

    return pd.DataFrame(series).sort_index()


def _evolution_to_curve(evolution: pd.Series) -> tuple[list[str], list[float]]:
    monthly = evolution.resample("ME").last().dropna()
    if monthly.empty:
        return [], []

    indexed = monthly / monthly.iloc[0] * CHART_BASE_VALUE
    labels = [index_date.strftime("%Y-%m") for index_date in indexed.index]
    values = [round(value, 2) for value in indexed.tolist()]
    return labels, values


def _benchmark_series_for_labels(
    labels: list[str],
    funds_dir: Path | None = None,
) -> list[float]:
    nav_df = load_fund_nav_csv(BENCHMARK_ISIN, funds_dir)
    if nav_df.empty or "nav" not in nav_df.columns:
        return []

    navs_df = pd.DataFrame({BENCHMARK_ISIN: nav_df["nav"]})
    evolution = calculate_buy_and_hold_returns(
        navs_df,
        {BENCHMARK_ISIN: 1.0},
        cash_weight=0.0,
    )
    if evolution.empty:
        return []

    bench_labels, bench_values = _evolution_to_curve(evolution["portfolio_base_1"])
    if not bench_labels:
        return []

    label_to_value = dict(zip(bench_labels, bench_values, strict=True))
    sorted_bench = sorted(label_to_value.items())

    aligned: list[float] = []
    for label in labels:
        value = None
        for bench_label, bench_value in sorted_bench:
            if bench_label <= label:
                value = bench_value
            else:
                break
        if value is None:
            return []
        aligned.append(value)

    return aligned


def build_equity_curve(
    positions: list[dict],
    funds_dir: Path | None = None,
) -> dict:
    """Compute buy-and-hold portfolio equity curve from local NAV CSV files."""
    weights, cash_weight = _portfolio_weights(positions)
    if not weights:
        return _empty_curve()

    navs_df = _load_portfolio_navs(weights, funds_dir)
    available = [isin for isin in weights if isin in navs_df.columns]
    if not available:
        return _empty_curve()

    fund_weights = {isin: weights[isin] for isin in available}
    invested_total = sum(fund_weights.values())
    if invested_total <= 0:
        return _empty_curve()

    if invested_total < 1.0:
        cash_weight = 1.0 - invested_total
    else:
        cash_weight = 0.0

    evolution = calculate_buy_and_hold_returns(
        navs_df[available],
        fund_weights,
        cash_weight=cash_weight,
    )
    if evolution.empty:
        return _empty_curve()

    labels, portfolio = _evolution_to_curve(evolution["portfolio_base_1"])
    if not labels:
        return _empty_curve()

    return {
        "benchmark_name": BENCHMARK_NAME,
        "as_of": date.today().isoformat(),
        "labels": labels,
        "portfolio": portfolio,
        "benchmark": _benchmark_series_for_labels(labels, funds_dir),
    }


def build_user_equity_curve(
    user_id: int,
    db_path=None,
    funds_dir: Path | None = None,
) -> dict:
    positions = list_user_portfolio(user_id, db_path)
    return build_equity_curve(positions, funds_dir)
