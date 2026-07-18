import datetime

import pandas as pd
from sqlmodel import select

from portfolio.api.database import get_session, init_db, upsert_alerts
from portfolio.api.models import Alert
from portfolio.job.alert_storage import extract_alert_values, persist_latest_alerts
from portfolio.common.macro_constants import SP500_DEATH_CROSS, YIELD_SPREAD_10Y3M
from portfolio.common.series import latest_series_date, save_series_csv


def test_latest_series_date_uses_last_row_in_file(tmp_path):
    series_dir = tmp_path / "series"
    df = pd.DataFrame(
        {"SP500": [4800.0, 4810.0]},
        index=pd.to_datetime(["2024-06-03", "2024-06-04"]),
    )
    save_series_csv("SP500", df, column_name="SP500", series_dir=series_dir)

    assert latest_series_date(series_dir) == datetime.date(2024, 6, 4)


def test_upsert_alerts_updates_existing_value(tmp_path):
    db_path = tmp_path / "portfolio.db"
    init_db(db_path)
    observation_date = datetime.date(2024, 6, 4)

    upsert_alerts(
        {"Sahm_Rule_Indicator": 0.32},
        observation_date,
        db_path,
    )
    upsert_alerts(
        {"Sahm_Rule_Indicator": 0.41},
        observation_date,
        db_path,
    )

    with get_session(db_path) as session:
        stored = session.exec(
            select(Alert).where(
                Alert.code == "Sahm_Rule_Indicator",
                Alert.date == observation_date,
            )
        ).one()

    assert stored.value == 0.41


def test_persist_latest_alerts_uses_series_file_date(tmp_path):
    db_path = tmp_path / "portfolio.db"
    series_dir = tmp_path / "series"
    init_db(db_path)

    save_series_csv(
        "SP500",
        pd.DataFrame({"SP500": [4800.0]}, index=pd.to_datetime(["2024-06-04"])),
        column_name="SP500",
        series_dir=series_dir,
    )

    market_df = pd.DataFrame(
        {
            "Unemployment_Rate": [3.8],
            "High_Yield_Spread": [3.25],
            "Financial_Stress_Index": [0.4],
            YIELD_SPREAD_10Y3M: [0.12],
            "Real_Interest_Rates": [1.8],
            "Sahm_Rule_Indicator": [0.32],
            "SP500": [4800.0],
            SP500_DEATH_CROSS: [1.02],
        },
        index=pd.to_datetime(["2024-06-04"]),
    )

    observation_date = persist_latest_alerts(
        market_df,
        series_dir=series_dir,
        db_path=db_path,
    )

    assert observation_date == datetime.date(2024, 6, 4)

    with get_session(db_path) as session:
        stored = {
            alert.code: alert.value
            for alert in session.exec(select(Alert)).all()
        }

    assert stored["Sahm_Rule_Indicator"] == 0.32
    assert stored["Unemployment_Rate"] == 3.8
    assert stored[SP500_DEATH_CROSS] == 1.02


def test_extract_alert_values_skips_missing_columns():
    row = pd.Series({"Sahm_Rule_Indicator": 0.25})
    values = extract_alert_values(row, ["Sahm_Rule_Indicator", SP500_DEATH_CROSS])

    assert values == {"Sahm_Rule_Indicator": 0.25}
