import datetime

import pandas as pd
from sqlmodel import select

from portfolio.api.database import get_session, init_db, upsert_signals
from portfolio.api.models import Signal
from portfolio.common.macro_constants import (
    FINANCIAL_STRESS,
    FINANCIAL_STRESS_INDEX,
    INVERTED_CURVE,
    MACRO_CRISIS_VOTES,
    MACRO_SYSTEM_LOCKED,
    SAHM_VALUE,
    SP500_CONFIRMED_DEATH_CROSS,
    SP500_DEATH_CROSS_ACTIVE,
    SP500_SMA_RATIO,
    YIELD_SPREAD_10Y3M,
)
from portfolio.common.series import latest_series_date, save_series_csv
from portfolio.common.signal_storage import extract_signal_values, persist_latest_signals


def test_latest_series_date_uses_last_row_in_file(tmp_path):
    series_dir = tmp_path / "series"
    df = pd.DataFrame(
        {"SP500": [4800.0, 4810.0]},
        index=pd.to_datetime(["2024-06-03", "2024-06-04"]),
    )
    save_series_csv("SP500", df, column_name="SP500", series_dir=series_dir)

    assert latest_series_date(series_dir) == datetime.date(2024, 6, 4)


def test_upsert_signals_updates_existing_value(tmp_path):
    db_path = tmp_path / "portfolio.db"
    init_db(db_path)
    observation_date = datetime.date(2024, 6, 4)

    upsert_signals(
        {"SAHM_RULE": 0.32},
        observation_date,
        db_path,
    )
    upsert_signals(
        {"SAHM_RULE": 0.41},
        observation_date,
        db_path,
    )

    with get_session(db_path) as session:
        stored = session.exec(
            select(Signal).where(
                Signal.code == "SAHM_RULE",
                Signal.date == observation_date,
            )
        ).one()

    assert stored.value == 0.41


def test_persist_latest_signals_uses_series_file_date(tmp_path):
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
            "SP500": [4800.0],
            SP500_SMA_RATIO: [1.0],
            INVERTED_CURVE: [False],
            SAHM_VALUE: [0.32],
            FINANCIAL_STRESS: [False],
            MACRO_CRISIS_VOTES: [1],
            MACRO_SYSTEM_LOCKED: [False],
            SP500_DEATH_CROSS_ACTIVE: [False],
            SP500_CONFIRMED_DEATH_CROSS: [False],
        },
        index=pd.to_datetime(["2024-06-04"]),
    )

    observation_date = persist_latest_signals(
        market_df,
        series_dir=series_dir,
        db_path=db_path,
    )

    assert observation_date == datetime.date(2024, 6, 4)

    with get_session(db_path) as session:
        stored = {
            signal.code: signal.value
            for signal in session.exec(select(Signal)).all()
        }

    assert stored["SAHM_RULE"] == 0.32
    assert stored["Unemployment_Rate"] == 3.8
    assert stored["INVERTED_CURVE"] == 0.0
    assert stored["MACRO_CRISIS_VOTES"] == 1.0
    assert stored["MACRO_SYSTEM_LOCKED"] == 0.0


def test_extract_signal_values_skips_missing_columns():
    row = pd.Series({SAHM_VALUE: 0.25})
    values = extract_signal_values(row, ["SAHM_RULE", "INVERTED_CURVE"])

    assert values == {"SAHM_RULE": 0.25}
