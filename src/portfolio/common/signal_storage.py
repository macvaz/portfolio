import datetime
from pathlib import Path

import pandas as pd

from portfolio.api.database import init_db, upsert_signals
from portfolio.common.series import latest_series_date
from portfolio.common.signal_dimensions import load_signal_dimension_fixture


def extract_signal_values(row: pd.Series, codes: list[str]) -> dict[str, float]:
    values: dict[str, float] = {}
    for code in codes:
        if code not in row.index:
            continue
        raw = row[code]
        if pd.isna(raw):
            continue
        values[code] = float(raw)
    return values


def persist_latest_signals(
    market_df: pd.DataFrame,
    *,
    series_dir: Path | None = None,
    db_path: Path | None = None,
) -> datetime.date | None:
    observation_date = latest_series_date(series_dir)
    if observation_date is None or market_df.empty:
        return None

    timestamp = pd.Timestamp(observation_date)
    if timestamp not in market_df.index:
        timestamp = market_df.index[-1]
        observation_date = timestamp.date()

    row = market_df.loc[timestamp]
    codes = [str(entry["code"]) for entry in load_signal_dimension_fixture()]
    values = extract_signal_values(row, codes)
    if not values:
        return None

    init_db(db_path)
    upsert_signals(values, observation_date, db_path)
    return observation_date
