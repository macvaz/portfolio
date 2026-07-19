from pathlib import Path

import pandas as pd

from portfolio.common.alert_descriptions import (
    alert_label,
    is_alert_active,
    is_alert_role,
    is_context_role,
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

CONTEXT_HISTORY_COLUMN_ORDER = (
    "Treasury_10Y_Yield",
    "Broad_Dollar_Index",
    "Reserve_Balances",
    "Overnight_RRP",
    "SOFR",
)

HISTORY_DISPLAY_ONLY_COLUMNS: dict[str, dict[str, str | None]] = {
    "SP500": {
        "description": "S&P 500 index level: broad U.S. large-cap equity benchmark (index).",
        "series_start": "1970-01-02",
    },
}


def _is_thresholded_alert(description: dict) -> bool:
    return is_alert_role(description) and description.get("threshold") is not None


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


def _fred_source_url(series_id: str | None, source: str | None) -> str | None:
    if source != "fred" or not series_id:
        return None
    return f"https://fred.stlouisfed.org/series/{series_id}"


def _column_payload(
    *,
    code: str,
    description: str,
    series_start: str | float | None = None,
    series_id: str | None = None,
    source: str | None = None,
    threshold: float | None = None,
    operator: str | None = None,
) -> dict[str, str | float | None]:
    return {
        "code": code,
        "label": alert_label(code),
        "description": description,
        "series_start": series_start,
        "identifier": series_id,
        "source_url": _fred_source_url(series_id, source),
        "threshold": threshold,
        "operator": operator,
    }


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
                _column_payload(
                    code=code,
                    description=str(display_only["description"]),
                    series_start=display_only.get("series_start"),
                )
            )
            continue
        if is_alert_role(row) and row.get("threshold") is not None:
            columns.append(
                _column_payload(
                    code=code,
                    description=str(row["description"]),
                    series_start=row.get("series_start"),
                    series_id=row.get("series_id"),
                    source=row.get("source"),
                    threshold=row.get("threshold"),
                    operator=row.get("operator"),
                )
            )
    return columns


def _context_history_columns(fixture: list[dict]) -> list[dict[str, str]]:
    fixture_by_code = {str(row["code"]): row for row in fixture}
    columns: list[dict[str, str]] = []
    for code in CONTEXT_HISTORY_COLUMN_ORDER:
        row = fixture_by_code.get(code)
        if row is None or not is_context_role(row):
            continue
        columns.append(
            _column_payload(
                code=code,
                description=str(row["description"]),
                series_start=row.get("series_start"),
                series_id=row.get("series_id"),
                source=row.get("source"),
                threshold=row.get("threshold"),
                operator=row.get("operator"),
            )
        )
    return columns


def _month_cell_value(
    row: pd.Series | None,
    code: str,
    description: dict,
    timestamp: pd.Timestamp,
) -> dict:
    if _month_before_series_start(timestamp, description.get("series_start")):
        return {"value": None, "active": None}
    raw = None if row is None else row.get(code)
    if raw is None or pd.isna(raw):
        return {"value": None, "active": None}
    value = float(raw)
    active = is_alert_active(
        value,
        description.get("threshold"),
        description.get("operator"),
    )
    return {"value": value, "active": active}


def build_monthly_alert_history(
    series_dir: Path | None = None,
    indexes_dir: Path | None = None,
) -> dict:
    fixture = load_alert_description_fixture()
    columns = _alert_history_columns(fixture)
    context_columns = _context_history_columns(fixture)
    market_df = load_market_dataframe(series_dir, indexes_dir)
    if market_df.empty:
        return {
            "columns": columns,
            "context_columns": context_columns,
            "rows": [],
        }

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
        values = [
            _month_cell_value(
                row,
                column["code"],
                descriptions_by_code[column["code"]],
                timestamp,
            )
            for column in columns
        ]
        context_values = [
            _month_cell_value(
                row,
                column["code"],
                descriptions_by_code[column["code"]],
                timestamp,
            )
            for column in context_columns
        ]

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
                "context_values": context_values,
                "active_count": active_count,
                "eligible_count": eligible_count,
            }
        )

    return {
        "columns": columns,
        "context_columns": context_columns,
        "rows": rows,
    }
