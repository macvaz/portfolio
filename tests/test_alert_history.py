import datetime

import pandas as pd

from portfolio.common.alert_history import build_monthly_alert_history
from portfolio.common.series import save_series_csv


def _write_monthly_series(tmp_path, series_id: str, values: dict[str, float]) -> None:
    dates = [pd.Timestamp(day) for day in values]
    frame = pd.DataFrame({"value": list(values.values())}, index=dates)
    save_series_csv(series_id, frame, column_name="value", series_dir=tmp_path)


def test_build_monthly_alert_history_pivots_alerts_by_month(tmp_path):
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

    assert len(history["rows"]) == 2
    assert history["rows"][0]["month"] == "2024-06"
    assert history["rows"][1]["month"] == "2024-05"

    june_unemployment = history["rows"][0]["values"][columns.index("Unemployment_Rate")]
    june_curve = history["rows"][0]["values"][columns.index("Yield_Spread_10Y3M")]
    june_sp500 = history["rows"][0]["values"][columns.index("SP500")]
    assert june_unemployment == {"value": 4.1, "active": False}
    assert june_curve == {"value": -0.1, "active": True}
    assert june_sp500 == {"value": 5100.0, "active": None}
    assert history["rows"][0]["active_count"] == 1


def test_build_monthly_alert_history_returns_empty_rows_without_series(tmp_path):
    history = build_monthly_alert_history(tmp_path)
    assert history["rows"] == []
    assert len(history["columns"]) == 8
