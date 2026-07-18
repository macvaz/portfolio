import datetime
from pathlib import Path

import pandas as pd

from portfolio.storage.database import init_db, upsert_alerts
from portfolio.common.alert_descriptions import load_alert_description_fixture
from portfolio.common.series import latest_series_date


def extract_alert_values(row: pd.Series, codes: list[str]) -> dict[str, float]:
    values: dict[str, float] = {}
    for code in codes:
        if code not in row.index:
            continue
        raw = row[code]
        if pd.isna(raw):
            continue
        values[code] = float(raw)
    return values


def persist_latest_alerts(
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
    codes = [str(entry["code"]) for entry in load_alert_description_fixture()]
    values = extract_alert_values(row, codes)
    if not values:
        return None

    init_db(db_path)
    upsert_alerts(values, observation_date, db_path)
    return observation_date
