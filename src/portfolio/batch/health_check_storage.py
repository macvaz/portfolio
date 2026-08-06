import datetime
from pathlib import Path

import pandas as pd

from portfolio.storage.database import upsert_health_checks
from portfolio.common.health_check_descriptions import (
    load_health_check_description_fixture,
)
from portfolio.common.indexes import latest_index_date


def extract_health_check_values(row: pd.Series, codes: list[str]) -> dict[str, float]:
    values: dict[str, float] = {}
    for code in codes:
        if code not in row.index:
            continue
        raw = row[code]
        if pd.isna(raw):
            continue
        values[code] = float(raw)
    return values


def persist_latest_health_checks(
    market_df: pd.DataFrame,
    *,
    indexes_dir: Path | None = None,
    db_path: Path | None = None,
) -> datetime.date | None:
    observation_date = latest_index_date(indexes_dir)
    if observation_date is None or market_df.empty:
        return None

    timestamp = pd.Timestamp(observation_date)
    if timestamp not in market_df.index:
        timestamp = market_df.index[-1]
        observation_date = timestamp.date()

    row = market_df.loc[timestamp]
    codes = [
        str(entry["code"]) for entry in load_health_check_description_fixture()
    ]
    values = extract_health_check_values(row, codes)
    if not values:
        return None

    upsert_health_checks(values, observation_date, db_path)
    return observation_date
