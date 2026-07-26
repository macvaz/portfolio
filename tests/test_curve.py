import pandas as pd
from datetime import date

from portfolio.api.services.portfolio.curve import (
    BENCHMARK_NAME,
    align_return_series,
    annualized_return_pct,
    annualized_volatility_pct,
    build_equity_curve,
    build_portfolio_daily_returns,
    returns_to_cumulative_curve,
)
from portfolio.common.navs import save_fund_nav_csv


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

    assert curve["labels"] == ["2024-02-29", "2024-03-31", "2024-04-30"]
    assert curve["portfolio"][0] != 0.0
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

    assert full["portfolio"] == [10.0, 21.0]
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

    assert curve["labels"] == ["2024-02-29", "2024-03-31"]
    assert curve["portfolio"] == [10.0, 21.0]
    assert curve["benchmark"] == [20.0, 40.0]


def test_build_equity_curve_empty_without_nav_files(tmp_path):
    positions = [{"isin": "ES0182527038", "weighted_assets": 1.0}]
    curve = build_equity_curve(positions, funds_dir=tmp_path / "funds")
    assert curve["labels"] == []
    assert curve["portfolio"] == []


def test_curve_matches_compounded_portfolio_returns(tmp_path):
    funds_dir = tmp_path / "funds"
    df = pd.DataFrame(
        {"value": [100.0, 110.0, 121.0]},
        index=pd.to_datetime(["2024-01-31", "2024-02-29", "2024-03-31"]),
    )
    save_fund_nav_csv("ES0182527038", df, funds_dir=funds_dir)
    positions = [{"isin": "ES0182527038", "weighted_assets": 1.0}]

    portfolio_returns = build_portfolio_daily_returns(positions, funds_dir=funds_dir)
    labels, portfolio_curve = returns_to_cumulative_curve(portfolio_returns)
    curve = build_equity_curve(positions, funds_dir=funds_dir)

    assert curve["labels"] == labels
    assert curve["portfolio"] == portfolio_curve


def test_annualized_return_pct_matches_quantstats_cagr():
    import quantstats as qs

    qs.extend_pandas()
    returns = pd.Series([0.0005] * 252)
    expected = float(qs.stats.cagr(returns) * 100)
    assert annualized_return_pct(returns) == round(expected, 2)


def test_annualized_volatility_pct_matches_quantstats():
    import quantstats as qs

    returns = pd.Series([0.01, -0.005, 0.002, 0.003, -0.001] * 50)
    expected = float(qs.stats.volatility(returns, periods=252, prepare_returns=False) * 100)
    assert annualized_volatility_pct(returns) == round(expected, 2)


def test_build_equity_curve_includes_annualized_performance(tmp_path):
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

    assert curve["portfolio_annualized_pct"] is not None
    assert curve["benchmark_annualized_pct"] is not None
    assert curve["portfolio_annualized_pct"] != curve["benchmark_annualized_pct"]
    assert curve["portfolio_volatility_pct"] is not None
    assert curve["benchmark_volatility_pct"] is not None
    assert curve["portfolio_volatility_pct"] != curve["benchmark_volatility_pct"]


def test_build_equity_curve_respects_start_date(tmp_path):
    funds_dir = tmp_path / "funds"
    df_portfolio = pd.DataFrame(
        {"value": [100.0, 110.0, 105.0, 126.0]},
        index=pd.to_datetime(["2024-01-31", "2024-02-29", "2024-03-31", "2024-04-30"]),
    )
    df_benchmark = pd.DataFrame(
        {"value": [100.0, 120.0, 108.0, 140.0]},
        index=pd.to_datetime(["2024-01-31", "2024-02-29", "2024-03-31", "2024-04-30"]),
    )
    save_fund_nav_csv("ES0182527038", df_portfolio, funds_dir=funds_dir)
    save_fund_nav_csv("IE00BYX5MX67", df_benchmark, funds_dir=funds_dir)

    full = build_equity_curve(
        [{"isin": "ES0182527038", "weighted_assets": 1.0}],
        funds_dir=funds_dir,
    )
    sliced = build_equity_curve(
        [{"isin": "ES0182527038", "weighted_assets": 1.0}],
        funds_dir=funds_dir,
        start_date=date(2024, 3, 31),
    )

    assert full["labels"] == ["2024-02-29", "2024-03-31", "2024-04-30"]
    assert sliced["labels"] == ["2024-03-31", "2024-04-30"]
    assert sliced["start_date"] == "2024-03-31"
    assert sliced["portfolio"][0] != 0.0
    assert sliced["portfolio"][-1] != full["portfolio"][-1]
    assert sliced["portfolio_volatility_pct"] != full["portfolio_volatility_pct"]
    assert sliced["benchmark_volatility_pct"] != full["benchmark_volatility_pct"]


def test_curve_total_matches_quantstats_cumulative_return():
    import quantstats as qs

    returns = pd.Series(
        [0.01, -0.005, 0.002, 0.003, -0.001] * 50,
        index=pd.bdate_range("2020-01-01", periods=250),
    )
    _, curve = returns_to_cumulative_curve(returns)
    expected = float(qs.stats.comp(returns) * 100)
    assert curve[-1] == round(expected, 2)
    assert annualized_return_pct(returns) == round(float(qs.stats.cagr(returns) * 100), 2)
