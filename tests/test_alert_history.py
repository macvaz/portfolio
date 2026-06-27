import pandas as pd

from portfolio.common.alert_history import (
    HISTORY_START_DATE,
    build_monthly_alert_history,
)
from portfolio.common.series import save_series_csv


def _write_monthly_series(tmp_path, series_id: str, values: dict[str, float]) -> None:
    dates = [pd.Timestamp(day) for day in values]
    frame = pd.DataFrame({"value": list(values.values())}, index=dates)
    save_series_csv(series_id, frame, column_name="value", series_dir=tmp_path)


def test_build_monthly_alert_history_pivots_alerts_by_month(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "portfolio.common.alert_history.DEFAULT_BACKTEST_SP500_PATH",
        tmp_path / "missing-sp500.csv",
    )
    monkeypatch.setattr(
        "portfolio.common.alert_history.HISTORY_START_DATE",
        pd.Timestamp("2024-01-01"),
    )
    _write_monthly_series(
        tmp_path,
        "UNRATE",
        {
            "2024-05-15": 3.9,
            "2024-06-15": 4.1,
        },
    )
    _write_monthly_series(
        tmp_path,
        "T10Y3M",
        {
            "2024-05-15": 0.2,
            "2024-06-15": -0.1,
        },
    )
    _write_monthly_series(
        tmp_path,
        "SP500",
        {
            "2024-05-15": 5000.0,
            "2024-06-15": 5100.0,
        },
    )

    history = build_monthly_alert_history(tmp_path)
    columns = [column["code"] for column in history["columns"]]
    assert columns == [
        "High_Yield_Spread",
        "Financial_Stress_Index",
        "Yield_Spread_10Y3M",
        "Real_Interest_Rates",
        "Unemployment_Rate",
        "Sahm_Rule_Indicator",
        "SP500_Death_Cross",
        "SP500",
    ]

    assert len(history["rows"]) == 6
    assert history["rows"][0]["month"] == "2024-06"
    assert history["rows"][1]["month"] == "2024-05"

    june_unemployment = history["rows"][0]["values"][columns.index("Unemployment_Rate")]
    june_curve = history["rows"][0]["values"][columns.index("Yield_Spread_10Y3M")]
    june_sp500 = history["rows"][0]["values"][columns.index("SP500")]
    june_hy = history["rows"][0]["values"][columns.index("High_Yield_Spread")]
    assert june_unemployment == {"value": 4.1, "active": False}
    assert june_curve == {"value": -0.1, "active": True}
    assert june_sp500 == {"value": 5100.0, "active": None}
    assert june_hy == {"value": None, "active": None}
    assert history["rows"][0]["active_count"] == 1
    assert history["rows"][0]["eligible_count"] == 7


def test_build_monthly_alert_history_fills_missing_months_from_1995(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "portfolio.common.alert_history.DEFAULT_BACKTEST_SP500_PATH",
        tmp_path / "missing-sp500.csv",
    )
    monkeypatch.setattr(
        "portfolio.common.alert_history.HISTORY_START_DATE",
        pd.Timestamp("1995-01-01"),
    )
    _write_monthly_series(
        tmp_path,
        "UNRATE",
        {"1995-02-15": 5.4},
    )

    history = build_monthly_alert_history(tmp_path)
    months = [row["month"] for row in history["rows"]]

    assert months == ["1995-02", "1995-01"]

    jan_1995 = next(row for row in history["rows"] if row["month"] == "1995-01")
    feb_1995 = next(row for row in history["rows"] if row["month"] == "1995-02")
    unemployment_idx = [
        index
        for index, column in enumerate(history["columns"])
        if column["code"] == "Unemployment_Rate"
    ][0]
    hy_idx = [
        index
        for index, column in enumerate(history["columns"])
        if column["code"] == "High_Yield_Spread"
    ][0]

    assert jan_1995["values"][unemployment_idx] == {"value": None, "active": None}
    assert feb_1995["values"][unemployment_idx]["value"] == 5.4
    assert jan_1995["values"][hy_idx] == {"value": None, "active": None}
    assert jan_1995["active_count"] == 0
    assert jan_1995["eligible_count"] == 5
    assert feb_1995["active_count"] == 1
    assert feb_1995["eligible_count"] == 5


def test_build_monthly_alert_history_honors_series_start(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "portfolio.common.alert_history.DEFAULT_BACKTEST_SP500_PATH",
        tmp_path / "missing-sp500.csv",
    )
    monkeypatch.setattr(
        "portfolio.common.alert_history.HISTORY_START_DATE",
        pd.Timestamp("2023-01-01"),
    )
    _write_monthly_series(
        tmp_path,
        "BAMLH0A0HYM2EY",
        {"2023-06-27": 8.5},
    )

    history = build_monthly_alert_history(tmp_path)
    hy_idx = [
        index
        for index, column in enumerate(history["columns"])
        if column["code"] == "High_Yield_Spread"
    ][0]

    may_2023 = next(row for row in history["rows"] if row["month"] == "2023-05")
    june_2023 = next(row for row in history["rows"] if row["month"] == "2023-06")
    assert may_2023["values"][hy_idx] == {"value": None, "active": None}
    assert may_2023["eligible_count"] == 6
    assert june_2023["values"][hy_idx]["value"] == 8.5
    assert june_2023["eligible_count"] == 7


def test_build_monthly_alert_history_returns_empty_rows_without_series(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(
        "portfolio.common.alert_history.DEFAULT_BACKTEST_SP500_PATH",
        tmp_path / "missing-sp500.csv",
    )
    history = build_monthly_alert_history(tmp_path)
    assert history["rows"] == []
    assert len(history["columns"]) == 8
