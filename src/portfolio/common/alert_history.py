from pathlib import Path

import pandas as pd

from portfolio.common.alert_descriptions import (
    is_alert_active,
    load_alert_description_fixture,
)
from portfolio.common.series import DEFAULT_SERIES_DIR, load_series_csv
from portfolio.common.signals import calculate_market_signals

ALERT_HISTORY_COLUMN_ORDER = (
    "High_Yield_Spread",
    "Financial_Stress_Index",
    "Yield_Spread_10Y3M",
    "Real_Interest_Rates",
    "Unemployment_Rate",
    "Sahm_Rule_Indicator",
    "SP500_Death_Cross",
    "SP500",
)

HISTORY_DISPLAY_ONLY_CODES = frozenset({"SP500"})


def load_market_dataframe_from_series(
    series_dir: Path | None = None,
) -> pd.DataFrame:
    root = series_dir or DEFAULT_SERIES_DIR
    fixture = load_alert_description_fixture()
    frames: list[pd.DataFrame] = []

    for entry in fixture:
        if entry.get("source") != "fred" or not entry.get("series_id"):
            continue
        series_id = str(entry["series_id"])
        code = str(entry["code"])
        series = load_series_csv(series_id, root)
        if series.empty:
            continue
        frames.append(series.rename(columns={series_id: code}))

    if not frames:
        return pd.DataFrame()

    df = frames[0]
    for frame in frames[1:]:
        df = df.join(frame, how="outer")
    df = df.sort_index().ffill().bfill()
    return calculate_market_signals(df)


def _alert_history_columns(fixture: list[dict]) -> list[dict[str, str]]:
    fixture_by_code = {str(row["code"]): row for row in fixture}
    columns: list[dict[str, str]] = []
    for code in ALERT_HISTORY_COLUMN_ORDER:
        row = fixture_by_code.get(code)
        if row is None:
            continue
        if row.get("threshold") is not None or code in HISTORY_DISPLAY_ONLY_CODES:
            columns.append(
                {
                    "code": code,
                    "description": str(row["description"]),
                }
            )
    return columns


def build_monthly_alert_history(
    series_dir: Path | None = None,
) -> dict:
    fixture = load_alert_description_fixture()
    columns = _alert_history_columns(fixture)
    market_df = load_market_dataframe_from_series(series_dir)
    if market_df.empty:
        return {"columns": columns, "rows": []}

    descriptions_by_code = {str(row["code"]): row for row in fixture}
    monthly = market_df.resample("ME").last().dropna(how="all")
    rows: list[dict] = []

    for timestamp, row in monthly.sort_index(ascending=False).iterrows():
        values: list[dict] = []
        for column in columns:
            code = column["code"]
            description = descriptions_by_code[code]
            raw = row.get(code)
            if raw is None or pd.isna(raw):
                values.append({"value": None, "active": None})
                continue
            value = float(raw)
            active = is_alert_active(
                value,
                description.get("threshold"),
                description.get("operator"),
            )
            values.append({"value": value, "active": active})

        active_count = sum(1 for cell in values if cell.get("active") is True)
        rows.append(
            {
                "month": timestamp.strftime("%Y-%m"),
                "values": values,
                "active_count": active_count,
            }
        )

    return {"columns": columns, "rows": rows}
