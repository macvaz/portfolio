from pathlib import Path

import pandas as pd

from portfolio.common.alert_descriptions import (
    is_alert_active,
    load_alert_description_fixture,
)
from portfolio.common.series import DEFAULT_SERIES_DIR, load_series_csv
from portfolio.common.signals import calculate_market_signals
from portfolio.datasources.sp500 import (
    DEFAULT_BACKTEST_SP500_PATH,
    load_backtest_sp500_csv,
)

HISTORY_START_DATE = pd.Timestamp("1995-01-01")

ALERT_HISTORY_COLUMN_ORDER = (
    "High_Yield_Spread",
    "Financial_Stress_Index",
    "Yield_Spread_10Y3M",
    "Real_Interest_Rates",
    "Unemployment_Rate",
    "Sahm_Rule_Indicator",
    "SP500_Death_Cross",
)

ALERT_HISTORY_COLUMN_LABELS = {
    "High_Yield_Spread": "High yield spread",
    "Financial_Stress_Index": "Financial stress",
    "Yield_Spread_10Y3M": "Curve inversion",
    "Real_Interest_Rates": "Real interest rate",
    "Unemployment_Rate": "Unemployment rate",
    "Sahm_Rule_Indicator": "Sahm rule",
    "SP500_Death_Cross": "SP500 death cross",
}


def _is_thresholded_alert(description: dict) -> bool:
    return description.get("threshold") is not None


def _count_monthly_alerts(
    timestamp: pd.Timestamp,
    columns: list[dict],
    values: list[dict],
    descriptions_by_code: dict[str, dict],
) -> tuple[int, int]:
    active_count = 0
    eligible_count = 0
    for column, cell in zip(columns, values, strict=True):
        code = column["code"]
        description = descriptions_by_code[code]
        if not _is_thresholded_alert(description):
            continue
        if _month_before_series_start(timestamp, description.get("series_start")):
            continue
        eligible_count += 1
        if cell.get("active") is True:
            active_count += 1
    return active_count, eligible_count


def _load_sp500_for_history(series_dir: Path) -> pd.DataFrame:
    if DEFAULT_BACKTEST_SP500_PATH.exists():
        return load_backtest_sp500_csv(
            start_date=HISTORY_START_DATE.strftime("%Y-%m-%d"),
        )
    series = load_series_csv("SP500", series_dir)
    if series.empty:
        return series
    return series.rename(columns={"SP500": "SP500"})


def _history_month_ends(until: pd.Timestamp) -> pd.DatetimeIndex:
    start = HISTORY_START_DATE + pd.offsets.MonthEnd(0)
    end = until + pd.offsets.MonthEnd(0)
    if end < start:
        return pd.DatetimeIndex([])
    return pd.date_range(start, end, freq="ME")


def load_market_dataframe_from_series(
    series_dir: Path | None = None,
) -> pd.DataFrame:
    root = series_dir or DEFAULT_SERIES_DIR
    fixture = load_alert_description_fixture()
    frames: list[pd.DataFrame] = []

    for entry in fixture:
        if entry.get("source") != "fred" or not entry.get("series_id"):
            continue
        code = str(entry["code"])
        series_id = str(entry["series_id"])
        series = load_series_csv(series_id, root)
        if series.empty:
            continue
        frames.append(series.rename(columns={series_id: code}))

    sp500 = _load_sp500_for_history(root)
    if not sp500.empty:
        frames.append(sp500)

    if not frames:
        return pd.DataFrame()

    df = frames[0]
    for frame in frames[1:]:
        df = df.join(frame, how="outer")
    return calculate_market_signals(df.sort_index())


def _month_before_series_start(
    month_end: pd.Timestamp,
    series_start: str | float | None,
) -> bool:
    if not series_start:
        return False
    return month_end.strftime("%Y-%m") < pd.Timestamp(series_start).strftime("%Y-%m")


def _alert_history_columns(fixture: list[dict]) -> list[dict[str, str]]:
    fixture_by_code = {str(row["code"]): row for row in fixture}
    columns: list[dict[str, str]] = []
    for code in ALERT_HISTORY_COLUMN_ORDER:
        row = fixture_by_code.get(code)
        if row is None:
            continue
        if row.get("threshold") is not None:
            columns.append(
                {
                    "code": code,
                    "label": ALERT_HISTORY_COLUMN_LABELS[code],
                    "description": str(row["description"]),
                    "series_start": row.get("series_start"),
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
    monthly = market_df.resample("ME").last()
    month_ends = _history_month_ends(monthly.index.max())
    rows: list[dict] = []

    for timestamp in reversed(month_ends):
        row = monthly.loc[timestamp] if timestamp in monthly.index else None
        values: list[dict] = []
        for column in columns:
            code = column["code"]
            description = descriptions_by_code[code]
            if _month_before_series_start(timestamp, description.get("series_start")):
                values.append({"value": None, "active": None})
                continue
            raw = None if row is None else row.get(code)
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

        active_count, eligible_count = _count_monthly_alerts(
            timestamp,
            columns,
            values,
            descriptions_by_code,
        )
        rows.append(
            {
                "month": timestamp.strftime("%Y-%m"),
                "values": values,
                "active_count": active_count,
                "eligible_count": eligible_count,
            }
        )

    return {"columns": columns, "rows": rows}
