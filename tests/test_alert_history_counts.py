import pandas as pd

from portfolio.api.services.alerts.history import _count_monthly_alerts


def test_count_monthly_alerts_uses_series_start_for_eligible_total():
    timestamp = pd.Timestamp("2003-06-30")
    columns = [
        {"code": "Unemployment_Rate"},
        {"code": "Real_Interest_Rates"},
        {"code": "High_Yield_Spread"},
    ]
    values = [
        {"value": 5.0, "active": False},
        {"value": 2.5, "active": True},
        {"value": None, "active": None},
    ]
    descriptions_by_code = {
        "Unemployment_Rate": {
            "threshold": 5.0,
            "series_start": "1990-01-01",
        },
        "Real_Interest_Rates": {
            "threshold": 2.0,
            "series_start": "2003-01-02",
        },
        "High_Yield_Spread": {
            "threshold": 9.0,
            "series_start": "2023-06-27",
        },
    }

    active_count, eligible_count = _count_monthly_alerts(
        timestamp,
        columns,
        values,
        descriptions_by_code,
    )

    assert active_count == 1
    assert eligible_count == 2
