import pandas as pd

from portfolio.api.curve import build_equity_curve
from portfolio.finance.nav_files import save_fund_nav_csv


def test_build_equity_curve_from_nav_files(tmp_path):
    funds_dir = tmp_path / "funds"
    df_a = pd.DataFrame(
        {"value": [100.0, 110.0, 121.0, 133.1]},
        index=pd.to_datetime(["2024-01-31", "2024-02-29", "2024-03-31", "2024-04-30"]),
    )
    df_b = pd.DataFrame(
        {"value": [200.0, 210.0, 220.5, 231.53]},
        index=pd.to_datetime(["2024-01-31", "2024-02-29", "2024-03-31", "2024-04-30"]),
    )
    save_fund_nav_csv("ES0182527038", df_a, funds_dir=funds_dir)
    save_fund_nav_csv("IE00BYX5NX33", df_b, funds_dir=funds_dir)

    positions = [
        {"isin": "ES0182527038", "weighted_assets": 0.6},
        {"isin": "IE00BYX5NX33", "weighted_assets": 0.4},
    ]

    curve = build_equity_curve(positions, funds_dir=funds_dir)

    assert curve["labels"] == ["2024-02", "2024-03", "2024-04"]
    assert curve["portfolio"][0] == 0.0
    assert curve["portfolio"][-1] > curve["portfolio"][0]
    assert curve["benchmark"] == []


def test_build_equity_curve_empty_without_positions(tmp_path):
    curve = build_equity_curve([], funds_dir=tmp_path / "funds")
    assert curve["labels"] == []
    assert curve["portfolio"] == []
    assert curve["benchmark"] == []


def test_build_equity_curve_reflects_partial_weights(tmp_path):
    funds_dir = tmp_path / "funds"
    df = pd.DataFrame(
        {"value": [100.0, 110.0, 121.0]},
        index=pd.to_datetime(["2024-01-31", "2024-02-29", "2024-03-31"]),
    )
    save_fund_nav_csv("ES0182527038", df, funds_dir=funds_dir)

    full = build_equity_curve(
        [{"isin": "ES0182527038", "weighted_assets": 1.0}],
        funds_dir=funds_dir,
    )
    partial = build_equity_curve(
        [{"isin": "ES0182527038", "weighted_assets": 0.25}],
        funds_dir=funds_dir,
    )

    assert full["portfolio"] == [0.0, 10.0]
    assert 0 < partial["portfolio"][-1] < full["portfolio"][-1]


def test_build_equity_curve_differs_by_portfolio_mix(tmp_path):
    funds_dir = tmp_path / "funds"
    df_a = pd.DataFrame(
        {"value": [100.0, 110.0, 121.0]},
        index=pd.to_datetime(["2024-01-31", "2024-02-29", "2024-03-31"]),
    )
    df_b = pd.DataFrame(
        {"value": [100.0, 130.0, 160.0]},
        index=pd.to_datetime(["2024-01-31", "2024-02-29", "2024-03-31"]),
    )
    save_fund_nav_csv("ES0182527038", df_a, funds_dir=funds_dir)
    save_fund_nav_csv("IE00BYX5NX33", df_b, funds_dir=funds_dir)

    curve_a = build_equity_curve(
        [{"isin": "ES0182527038", "weighted_assets": 1.0}],
        funds_dir=funds_dir,
    )
    curve_b = build_equity_curve(
        [{"isin": "IE00BYX5NX33", "weighted_assets": 1.0}],
        funds_dir=funds_dir,
    )

    assert curve_a["portfolio"][-1] != curve_b["portfolio"][-1]


def test_build_equity_curve_includes_sp500_benchmark(tmp_path):
    funds_dir = tmp_path / "funds"
    df_portfolio = pd.DataFrame(
        {"value": [100.0, 110.0, 121.0]},
        index=pd.to_datetime(["2024-01-31", "2024-02-29", "2024-03-31"]),
    )
    df_benchmark = pd.DataFrame(
        {"value": [100.0, 120.0, 140.0]},
        index=pd.to_datetime(["2024-01-31", "2024-02-29", "2024-03-31"]),
    )
    save_fund_nav_csv("ES0182527038", df_portfolio, funds_dir=funds_dir)
    save_fund_nav_csv("IE00BYX5MX67", df_benchmark, funds_dir=funds_dir)

    curve = build_equity_curve(
        [{"isin": "ES0182527038", "weighted_assets": 1.0}],
        funds_dir=funds_dir,
    )

    assert curve["labels"] == ["2024-02", "2024-03"]
    assert curve["portfolio"] == [0.0, 10.0]
    assert curve["benchmark"] == [0.0, 16.67]


def test_build_equity_curve_empty_without_nav_files(tmp_path):
    positions = [{"isin": "ES0182527038", "weighted_assets": 1.0}]
    curve = build_equity_curve(positions, funds_dir=tmp_path / "funds")
    assert curve["labels"] == []
    assert curve["portfolio"] == []

