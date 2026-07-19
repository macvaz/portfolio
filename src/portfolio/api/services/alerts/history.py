from pathlib import Path

import pandas as pd

from portfolio.common.alert_descriptions import (
    alert_label,
    is_alert_active,
    load_alert_description_fixture,
)
from portfolio.common.market import load_market_dataframe

HISTORY_START_DATE = pd.Timestamp("1995-01-01")

ALERT_HISTORY_COLUMN_ORDER = (
    "Unemployment_Rate",
    "High_Yield_Spread",
    "Financial_Stress_Index",
    "Real_Interest_Rates",
    "Breakeven_Inflation",
    "Yield_Spread_10Y3M",
    "SP500_Death_Cross",
    "SP500",
)

HISTORY_DISPLAY_ONLY_COLUMNS: dict[str, dict[str, str | None]] = {
    "SP500": {
        "description": "S&P 500 index level: broad U.S. large-cap equity benchmark (index).",
        "series_start": "1970-01-02",
    },
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


def _history_month_ends(until: pd.Timestamp) -> pd.DatetimeIndex:
    start = HISTORY_START_DATE + pd.offsets.MonthEnd(0)
    end = until + pd.offsets.MonthEnd(0)
    if end < start:
        return pd.DatetimeIndex([])
    return pd.date_range(start, end, freq="ME")


def load_market_dataframe_from_series(
    series_dir: Path | None = None,
    indexes_dir: Path | None = None,
) -> pd.DataFrame:
    """Load the market DataFrame used by alert history (shared builder)."""
    return load_market_dataframe(series_dir, indexes_dir)


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
            display_only = HISTORY_DISPLAY_ONLY_COLUMNS.get(code)
            if display_only is None:
                continue
            columns.append(
                {
                    "code": code,
                    "label": alert_label(code),
                    "description": str(display_only["description"]),
                    "series_start": display_only.get("series_start"),
                }
            )
            continue
        if row.get("threshold") is not None:
            columns.append(
                {
                    "code": code,
                    "label": alert_label(code),
                    "description": str(row["description"]),
                    "series_start": row.get("series_start"),
                }
            )
    return columns


def build_monthly_alert_history(
    series_dir: Path | None = None,
    indexes_dir: Path | None = None,
) -> dict:
    fixture = load_alert_description_fixture()
    columns = _alert_history_columns(fixture)
    market_df = load_market_dataframe(series_dir, indexes_dir)
    if market_df.empty:
        return {"columns": columns, "rows": []}

    descriptions_by_code = {str(row["code"]): row for row in fixture}
    for code, meta in HISTORY_DISPLAY_ONLY_COLUMNS.items():
        descriptions_by_code[code] = {
            "threshold": None,
            "operator": None,
            "series_start": meta.get("series_start"),
        }
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
