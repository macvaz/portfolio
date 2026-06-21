from datetime import date

import pandas as pd

from portfolio.api.database import get_fund_metrics, init_db, save_fund
from portfolio.common.metrics import (
    compute_fund_metrics,
    compute_metrics,
    compute_portfolio_metrics,
    update_all_fund_metrics,
)
from portfolio.common.navs import save_fund_nav_csv


def _daily_navs(start: str, returns: list[float]) -> pd.DataFrame:
    nav = 100.0
    rows = [(start, nav)]
    current = pd.Timestamp(start)
    for daily_return in returns:
        current += pd.Timedelta(days=1)
        nav *= 1 + daily_return
        rows.append((current.strftime("%Y-%m-%d"), nav))
    return pd.DataFrame(
        {"value": [row[1] for row in rows]},
        index=pd.to_datetime([row[0] for row in rows]),
    )


def test_compute_metrics_from_daily_returns():
    fund_returns = pd.Series(
        [0.01, -0.005, 0.008, 0.002], index=pd.date_range("2024-01-02", periods=4)
    )
    benchmark_returns = pd.Series(
        [0.008, -0.004, 0.006, 0.001], index=fund_returns.index
    )

    metrics = compute_metrics(fund_returns, benchmark_returns)

    assert metrics["pct_1w"] == 1.5
    assert metrics["beta_6m"] is not None
    assert metrics["cor_6m"] is not None
    assert metrics["vol_1y"] is not None
    assert metrics["sr_6m"] is not None
    assert metrics["sr_1y"] is not None


def test_compute_fund_metrics_uses_benchmark(tmp_path):
    funds_dir = tmp_path / "funds"
    fund_navs = _daily_navs("2024-01-01", [0.01, -0.005, 0.008, 0.002, 0.004])
    benchmark_navs = _daily_navs("2024-01-01", [0.008, -0.004, 0.006, 0.001, 0.003])
    save_fund_nav_csv("ES0182527038", fund_navs, funds_dir=funds_dir)
    save_fund_nav_csv("IE00BYX5MX67", benchmark_navs, funds_dir=funds_dir)

    metrics = compute_fund_metrics("ES0182527038", funds_dir=funds_dir)

    assert metrics["pct_1w"] == 1.91
    assert metrics["beta_6m"] is not None
    assert metrics["cor_6m"] is not None


def test_compute_portfolio_metrics_from_positions(tmp_path):
    funds_dir = tmp_path / "funds"
    save_fund_nav_csv(
        "ES0182527038",
        _daily_navs("2024-01-01", [0.01, -0.005, 0.008, 0.002, 0.004]),
        funds_dir=funds_dir,
    )
    save_fund_nav_csv(
        "IE00BYX5NX33",
        _daily_navs("2024-01-01", [0.005, 0.004, -0.002, 0.003, 0.001]),
        funds_dir=funds_dir,
    )
    save_fund_nav_csv(
        "IE00BYX5MX67",
        _daily_navs("2024-01-01", [0.008, -0.004, 0.006, 0.001, 0.003]),
        funds_dir=funds_dir,
    )

    metrics = compute_portfolio_metrics(
        [
            {"isin": "ES0182527038", "weighted_assets": 0.6},
            {"isin": "IE00BYX5NX33", "weighted_assets": 0.4},
        ],
        funds_dir=funds_dir,
    )

    assert metrics["pct_1w"] is not None
    assert metrics["beta_6m"] is not None


def test_update_all_fund_metrics_persists_to_database(tmp_path):
    db_path = tmp_path / "portfolio.db"
    funds_dir = tmp_path / "funds"
    init_db(db_path)
    save_fund("ES0182527038", "Test Fund", "F0GBR04KHC", db_path=db_path)
    save_fund_nav_csv(
        "ES0182527038",
        _daily_navs("2024-01-01", [0.01, -0.005, 0.008, 0.002, 0.004]),
        funds_dir=funds_dir,
    )
    save_fund_nav_csv(
        "IE00BYX5MX67",
        _daily_navs("2024-01-01", [0.008, -0.004, 0.006, 0.001, 0.003]),
        funds_dir=funds_dir,
    )

    updated = update_all_fund_metrics(db_path, funds_dir)

    assert updated == 1
    stored = get_fund_metrics("ES0182527038", db_path)
    assert stored["pct_1w"] == 1.91
    assert stored["beta_6m"] is not None


def test_ytd_return_uses_current_year_only():
    year = date.today().year
    previous_year = pd.date_range(f"{year - 1}-12-28", periods=3, freq="D")
    current_year = pd.date_range(f"{year}-01-02", periods=2, freq="D")
    index = previous_year.append(current_year)
    returns = pd.Series([0.10, 0.10, 0.10, 0.02, 0.03], index=index)

    metrics = compute_metrics(returns)

    assert metrics["pct_ytd"] == 5.06
