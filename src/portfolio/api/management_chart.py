"""Buy-and-hold portfolio chart for the management screen."""

from pathlib import Path

import pandas as pd

from portfolio.finance.nav_files import load_fund_nav_csv
from portfolio.finance.returns import calculate_buy_and_hold_returns

CHART_BASE_VALUE = 100.0


def _mock_benchmark_series(length: int, drift: float = 0.0042) -> list[float]:
    if length == 0:
        return []

    value = CHART_BASE_VALUE
    series: list[float] = []
    for _ in range(length):
        series.append(round(value, 2))
        value *= 1 + drift
    return series


def _empty_chart() -> dict:
    return {"labels": [], "portfolio": [], "benchmark": []}


def _normalize_weights(positions: list[dict]) -> dict[str, float]:
    weights = {
        position["isin"]: float(position["weighted_assets"])
        for position in positions
        if float(position["weighted_assets"]) > 0
    }
    total = sum(weights.values())
    if total <= 0:
        return {}
    return {isin: weight / total for isin, weight in weights.items()}


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


def _evolution_to_chart_series(evolution: pd.Series) -> tuple[list[str], list[float]]:
    monthly = evolution.resample("ME").last().dropna()
    if monthly.empty:
        return [], []

    indexed = monthly / monthly.iloc[0] * CHART_BASE_VALUE
    labels = [date.strftime("%Y-%m") for date in indexed.index]
    values = [round(value, 2) for value in indexed.tolist()]
    return labels, values


def build_portfolio_chart(
    positions: list[dict],
    funds_dir: Path | None = None,
) -> dict:
    """Return chart payload with real buy-and-hold portfolio performance."""
    weights = _normalize_weights(positions)
    if not weights:
        return _empty_chart()

    navs_df = _load_portfolio_navs(weights, funds_dir)
    available = [isin for isin in weights if isin in navs_df.columns]
    if not available:
        return _empty_chart()

    nav_weights = {isin: weights[isin] for isin in available}
    total = sum(nav_weights.values())
    nav_weights = {isin: weight / total for isin, weight in nav_weights.items()}

    navs_df = navs_df[available]
    evolution = calculate_buy_and_hold_returns(navs_df, nav_weights)
    if evolution.empty:
        return _empty_chart()

    labels, portfolio = _evolution_to_chart_series(evolution["portfolio_base_1"])
    if not labels:
        return _empty_chart()

    return {
        "labels": labels,
        "portfolio": portfolio,
        "benchmark": _mock_benchmark_series(len(labels)),
    }
