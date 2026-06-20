import pandas as pd

from portfolio.api.management_chart import build_portfolio_chart
from portfolio.finance.nav_files import save_fund_nav_csv


def test_build_portfolio_chart_from_nav_files(tmp_path):
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

    chart = build_portfolio_chart(positions, funds_dir=funds_dir)

    assert chart["labels"] == ["2024-02", "2024-03", "2024-04"]
    assert chart["portfolio"][0] == 100.0
    assert chart["portfolio"][-1] > chart["portfolio"][0]
    assert len(chart["benchmark"]) == len(chart["portfolio"])


def test_build_portfolio_chart_empty_without_positions(tmp_path):
    chart = build_portfolio_chart([], funds_dir=tmp_path / "funds")
    assert chart == {"labels": [], "portfolio": [], "benchmark": []}


def test_build_portfolio_chart_empty_without_nav_files(tmp_path):
    positions = [{"isin": "ES0182527038", "weighted_assets": 1.0}]
    chart = build_portfolio_chart(positions, funds_dir=tmp_path / "funds")
    assert chart == {"labels": [], "portfolio": [], "benchmark": []}
