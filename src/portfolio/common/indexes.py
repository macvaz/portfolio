import datetime
from pathlib import Path

import pandas as pd

DEFAULT_INDEXES_DIR = Path("data/indexes")


def index_path(index_id: str, indexes_dir: Path | None = None) -> Path:
    root = indexes_dir or DEFAULT_INDEXES_DIR
    return root / f"{index_id}.csv"


def index_dataframe_to_csv(df: pd.DataFrame, column_name: str) -> pd.DataFrame:
    """Normalize a downloaded index series to ``date`` and ``value`` columns."""
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
        raise ValueError(f"Cannot determine value column for index {column_name!r}")

    if "date" not in out.columns:
        out = out.reset_index()
        date_col = out.columns[0]
        out = out.rename(columns={date_col: "date"})

    out = out.rename(columns={value_col: "value"})
    out["date"] = pd.to_datetime(out["date"]).dt.strftime("%Y-%m-%d")
    return out[["date", "value"]].sort_values("date")


def save_index_csv(
    index_id: str,
    df: pd.DataFrame,
    *,
    column_name: str | None = None,
    indexes_dir: Path | None = None,
) -> Path:
    path = index_path(index_id, indexes_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    index_dataframe_to_csv(df, column_name or index_id).to_csv(path, index=False)
    return path


def load_index_csv(index_id: str, indexes_dir: Path | None = None) -> pd.DataFrame:
    path = index_path(index_id, indexes_dir)
    if not path.exists():
        return pd.DataFrame()

    df = pd.read_csv(path, parse_dates=["date"])
    return df.set_index("date").rename(columns={"value": index_id}).sort_index()


def latest_index_date(
    indexes_dir: Path | None = None,
    index_id: str = "SP500",
) -> datetime.date | None:
    """Return the last observation date stored for an index CSV."""
    series = load_index_csv(index_id, indexes_dir)
    if series.empty:
        return None
    return series.index.max().date()
