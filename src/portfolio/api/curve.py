"""Real portfolio equity curve from stored NAV files."""

from datetime import date
from pathlib import Path

import pandas as pd

from portfolio.api.database import list_user_portfolio
from portfolio.finance.nav_files import load_fund_nav_csv
from portfolio.finance.returns import calculate_buy_and_hold_returns

BENCHMARK_NAME = "S&P 500"
BENCHMARK_ISIN = "IE00BYX5MX67"
TRADING_DAYS_PER_YEAR = 252


def _empty_curve() -> dict:
    return {
        "benchmark_name": BENCHMARK_NAME,
        "benchmark_isin": BENCHMARK_ISIN,
        "portfolio_annualized_pct": None,
        "benchmark_annualized_pct": None,
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


def returns_to_cumulative_curve(returns: pd.Series) -> tuple[list[str], list[float]]:
    """Convert daily simple returns to a cumulative % curve starting at zero."""
    returns = returns.dropna()
    if returns.empty:
        return [], []

    wealth = (1 + returns).cumprod()
    cumulative_pct = (wealth / wealth.iloc[0] - 1.0) * 100.0
    labels = [index_date.strftime("%Y-%m-%d") for index_date in cumulative_pct.index]
    values = [round(float(value), 2) for value in cumulative_pct.tolist()]
    return labels, values


def annualized_return_pct(
    returns: pd.Series,
    periods_per_year: int = TRADING_DAYS_PER_YEAR,
) -> float | None:
    """CAGR from daily returns, matching QuantStats (252 trading days per year)."""
    returns = returns.dropna()
    if returns.empty:
        return None

    total_return = (1 + returns).prod() - 1
    years = len(returns) / periods_per_year
    if years <= 0:
        return None

    annualized = (1 + total_return) ** (1 / years) - 1
    return round(float(annualized * 100), 2)


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


def build_equity_curve(
    positions: list[dict],
    funds_dir: Path | None = None,
) -> dict:
    """Compute buy-and-hold portfolio equity curve from local NAV CSV files."""
    portfolio_returns = build_portfolio_daily_returns(positions, funds_dir)
    if portfolio_returns is None or portfolio_returns.empty:
        return _empty_curve()

    benchmark_returns = load_benchmark_daily_returns(funds_dir)
    portfolio_returns, benchmark_returns = align_return_series(
        portfolio_returns,
        benchmark_returns,
    )

    labels, portfolio = returns_to_cumulative_curve(portfolio_returns)
    if not labels:
        return _empty_curve()

    benchmark: list[float] = []
    benchmark_annualized_pct = None
    if benchmark_returns is not None and not benchmark_returns.empty:
        _, benchmark = returns_to_cumulative_curve(benchmark_returns)
        benchmark_annualized_pct = annualized_return_pct(benchmark_returns)

    return {
        "benchmark_name": BENCHMARK_NAME,
        "benchmark_isin": BENCHMARK_ISIN,
        "portfolio_annualized_pct": annualized_return_pct(portfolio_returns),
        "benchmark_annualized_pct": benchmark_annualized_pct,
        "as_of": date.today().isoformat(),
        "labels": labels,
        "portfolio": portfolio,
        "benchmark": benchmark,
    }


def build_user_equity_curve(
    user_id: int,
    db_path=None,
    funds_dir: Path | None = None,
) -> dict:
    positions = list_user_portfolio(user_id, db_path)
    return build_equity_curve(positions, funds_dir)
