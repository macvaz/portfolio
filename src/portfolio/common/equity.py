"""Shared equity/return helpers used by metrics, curve, and risk reports."""

from pathlib import Path

import numpy as np
import pandas as pd

from portfolio.common.navs import load_fund_nav_csv

BENCHMARK_NAME = "S&P 500"
BENCHMARK_ISIN = "IE00BYX5MX67"
TRADING_DAYS_PER_YEAR = 252


def calculate_buy_and_hold_returns(
    navs_df: pd.DataFrame,
    portfolio: dict[str, float],
    cash_weight: float = 0.0,
) -> pd.DataFrame:
    """Calculate buy-and-hold portfolio evolution from asset NAVs.

    Converts price series to returns, applies initial weights without rebalancing,
    and returns the total portfolio value indexed to base 1.
    """
    navs_df = navs_df.dropna()
    returns_df = navs_df.pct_change().dropna()
    weights = [portfolio[isin] for isin in returns_df.columns]
    weights = np.array(weights)

    individual_assets_base_1 = (1 + returns_df).cumprod()
    weighted_assets = individual_assets_base_1 * weights

    portfolio_evolution = pd.DataFrame(index=returns_df.index)
    portfolio_evolution["portfolio_base_1"] = weighted_assets.sum(axis=1) + cash_weight

    return portfolio_evolution


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


def _load_benchmark_nav(funds_dir: Path | None = None) -> pd.Series | None:
    nav_df = load_fund_nav_csv(BENCHMARK_ISIN, funds_dir)
    if nav_df.empty or "nav" not in nav_df.columns:
        return None
    return nav_df["nav"]


def load_benchmark_daily_returns(funds_dir: Path | None = None) -> pd.Series | None:
    """Daily simple returns for the benchmark fund from stored NAV data."""
    nav = _load_benchmark_nav(funds_dir)
    if nav is None:
        return None

    returns = nav.pct_change().dropna()
    if returns.empty:
        return None

    returns.name = BENCHMARK_NAME
    return returns


def align_return_series(
    portfolio: pd.Series,
    benchmark: pd.Series | None,
) -> tuple[pd.Series, pd.Series | None]:
    """Align portfolio and benchmark daily returns on shared dates."""
    portfolio = portfolio.dropna()
    if benchmark is None or benchmark.empty:
        return portfolio, None

    aligned = pd.concat(
        {"portfolio": portfolio, "benchmark": benchmark},
        axis=1,
        join="inner",
    ).dropna()
    if aligned.empty:
        return portfolio, None

    portfolio_out = aligned["portfolio"]
    benchmark_out = aligned["benchmark"]
    portfolio_out.name = portfolio.name
    benchmark_out.name = benchmark.name
    return portfolio_out, benchmark_out


def build_portfolio_evolution(
    positions: list[dict],
    funds_dir: Path | None = None,
) -> pd.Series | None:
    """Return buy-and-hold portfolio evolution indexed to 1.0, or None."""
    weights, cash_weight = _portfolio_weights(positions)
    if not weights:
        return None

    navs_df = _load_portfolio_navs(weights, funds_dir)
    available = [isin for isin in weights if isin in navs_df.columns]
    if not available:
        return None

    fund_weights = {isin: weights[isin] for isin in available}
    invested_total = sum(fund_weights.values())
    if invested_total <= 0:
        return None

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
        return None

    return evolution["portfolio_base_1"]


def build_portfolio_daily_returns(
    positions: list[dict],
    funds_dir: Path | None = None,
) -> pd.Series | None:
    """Daily simple buy-and-hold portfolio returns used by curve and QuantStats."""
    evolution = build_portfolio_evolution(positions, funds_dir)
    if evolution is None or evolution.empty:
        return None

    returns = evolution.pct_change()
    # Evolution is indexed from the first return date with base 1.0 on the prior day.
    returns.iloc[0] = evolution.iloc[0] - 1.0
    returns = returns.dropna()
    if returns.empty:
        return None

    returns.name = "Portfolio"
    return returns
