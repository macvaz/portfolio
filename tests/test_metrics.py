from datetime import date

import pandas as pd

from portfolio.storage.database import get_fund_metrics, init_db, save_fund
from portfolio.common.metrics import (
    compute_aligned_recent_daily_returns,
    compute_fund_metrics,
    compute_metrics,
    compute_portfolio_correlation_matrix,
    compute_portfolio_metrics,
    compute_portfolio_ter,
)
from portfolio.batch.metrics import update_all_fund_metrics
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


def test_compute_portfolio_ter_weighted_average():
    ter = compute_portfolio_ter(
        [
            {"isin": "A", "weighted_assets": 0.6, "ter": 1.0},
            {"isin": "B", "weighted_assets": 0.4, "ter": 0.1},
        ]
    )
    assert ter == 0.64


def test_compute_portfolio_ter_cash_lowers_average():
    # 50% invested at 1.0% TER, 50% cash → portfolio TER 0.50
    assert (
        compute_portfolio_ter([{"isin": "A", "weighted_assets": 0.5, "ter": 1.0}])
        == 0.5
    )


def test_compute_portfolio_ter_requires_all_positions():
    assert (
        compute_portfolio_ter(
            [
                {"isin": "A", "weighted_assets": 0.5, "ter": 1.0},
                {"isin": "B", "weighted_assets": 0.5, "ter": None},
            ]
        )
        is None
    )


def test_compute_portfolio_correlation_matrix(tmp_path):
    funds_dir = tmp_path / "funds"
    # Highly correlated pair: same return path with tiny noise on the second.
    base = [0.01, -0.005, 0.008, 0.002, 0.004, -0.003, 0.006, 0.001]
    save_fund_nav_csv(
        "ES0182527038",
        _daily_navs("2024-01-01", base),
        funds_dir=funds_dir,
    )
    save_fund_nav_csv(
        "IE00BYX5NX33",
        _daily_navs("2024-01-01", [r + 0.0001 for r in base]),
        funds_dir=funds_dir,
    )
    save_fund_nav_csv(
        "LU1234567890",
        _daily_navs("2024-01-01", [-0.01, 0.012, -0.008, 0.015, -0.004, 0.009, -0.002, 0.003]),
        funds_dir=funds_dir,
    )

    result = compute_portfolio_correlation_matrix(
        [
            {"isin": "ES0182527038", "name": "Fund Alpha", "weighted_assets": 0.4},
            {"isin": "IE00BYX5NX33", "name": "Fund Beta", "weighted_assets": 0.3},
            {"isin": "LU1234567890", "name": "Fund Gamma", "weighted_assets": 0.3},
        ],
        funds_dir=funds_dir,
    )

    assert result is not None
    assert result["window"] == "6m"
    assert [label["isin"] for label in result["labels"]] == [
        "ES0182527038",
        "IE00BYX5NX33",
        "LU1234567890",
    ]
    assert len(result["matrix"]) == 3
    assert all(len(row) == 3 for row in result["matrix"])
    assert result["matrix"][0][0] == 1.0
    assert result["matrix"][1][1] == 1.0
    assert result["matrix"][0][1] == result["matrix"][1][0]
    assert result["matrix"][0][1] > 0.99


def test_compute_portfolio_correlation_matrix_requires_two_funds(tmp_path):
    funds_dir = tmp_path / "funds"
    save_fund_nav_csv(
        "ES0182527038",
        _daily_navs("2024-01-01", [0.01, -0.005, 0.008]),
        funds_dir=funds_dir,
    )

    assert (
        compute_portfolio_correlation_matrix(
            [{"isin": "ES0182527038", "name": "Only Fund", "weighted_assets": 1.0}],
            funds_dir=funds_dir,
        )
        is None
    )


def test_compute_aligned_recent_daily_returns(tmp_path):
    funds_dir = tmp_path / "funds"
    # Fund A has returns through 01-06; fund B stops earlier (missing latest days).
    save_fund_nav_csv(
        "AAA",
        _daily_navs("2024-01-01", [0.01, 0.02, -0.01, 0.005, 0.003, 0.004]),
        funds_dir=funds_dir,
    )
    save_fund_nav_csv(
        "BBB",
        _daily_navs("2024-01-01", [0.01, -0.02, 0.015, 0.002]),
        funds_dir=funds_dir,
    )

    result = compute_aligned_recent_daily_returns(
        [
            {"isin": "AAA", "name": "Fund A", "weighted_assets": 0.6},
            {"isin": "BBB", "name": "Fund B", "weighted_assets": 0.4},
        ],
        days=5,
        funds_dir=funds_dir,
    )

    assert result["dates"] == [
        "2024-01-07",
        "2024-01-06",
        "2024-01-05",
        "2024-01-04",
        "2024-01-03",
    ]
    by_isin = {fund["isin"]: fund for fund in result["funds"]}
    assert by_isin["AAA"]["returns"] == [0.4, 0.3, 0.5, -1.0, 2.0]
    assert by_isin["BBB"]["returns"] == [None, None, 0.2, 1.5, -2.0]


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
