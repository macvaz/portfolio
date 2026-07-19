from pathlib import Path

import pandas as pd

DEFAULT_SERIES_DIR = Path("data/series")


def series_path(series_id: str, series_dir: Path | None = None) -> Path:
    root = series_dir or DEFAULT_SERIES_DIR
    return root / f"{series_id}.csv"


def series_dataframe_to_csv(df: pd.DataFrame, column_name: str) -> pd.DataFrame:
    """Normalize a downloaded FRED series to ``date`` and ``value`` columns."""
    if df.empty:
        return pd.DataFrame(columns=["date", "value"])

    out = df.copy()
    if column_name in out.columns:
        value_col = column_name
    elif "value" in out.columns:
        value_col = "value"
    elif len(out.columns) == 1:
        value_col = out.columns[0]
    else:
        raise ValueError(f"Cannot determine value column for series {column_name!r}")

    if "date" not in out.columns:
        out = out.reset_index()
        date_col = out.columns[0]
        out = out.rename(columns={date_col: "date"})

    out = out.rename(columns={value_col: "value"})
    out["date"] = pd.to_datetime(out["date"]).dt.strftime("%Y-%m-%d")
    return out[["date", "value"]].sort_values("date")


def save_series_csv(
    series_id: str,
    df: pd.DataFrame,
    *,
    column_name: str | None = None,
    series_dir: Path | None = None,
) -> Path:
    path = series_path(series_id, series_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    series_dataframe_to_csv(df, column_name or series_id).to_csv(path, index=False)
    return path


def load_series_csv(series_id: str, series_dir: Path | None = None) -> pd.DataFrame:
    path = series_path(series_id, series_dir)
    if not path.exists():
        return pd.DataFrame()

    df = pd.read_csv(path, parse_dates=["date"])
    return df.set_index("date").rename(columns={"value": series_id}).sort_index()
