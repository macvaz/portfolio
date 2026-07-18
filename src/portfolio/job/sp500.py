"""Download S&P 500 index history from Morningstar."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from portfolio.datasources.morningstar import download_navs

DEFAULT_BACKTEST_SP500_PATH = Path("data/backtest/sp500.csv")
# Morningstar security ID for the S&P 500 price index (long-term daily history).
SP500_SECURITY_ID = "XIUSA000OA"


def _download_sp500_closes(
    start_date: str | None = None,
    end_date: str | None = None,
) -> pd.Series:
    start = start_date or "1950-01-01"
    end = end_date or date.today().isoformat()
    history = download_navs(
        fund_id=SP500_SECURITY_ID,
        start=start,
        end=end,
        currency="USD",
    )
    if history.empty or "value" not in history.columns:
        return pd.Series(dtype=float, name="SP500")

    close = history["value"].copy()
    close.name = "SP500"
    close.index = pd.to_datetime(close.index).tz_localize(None).normalize()
    return close.sort_index()


def download_sp500(
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    """Download daily S&P 500 close levels for the signals pipeline."""
    return _download_sp500_closes(start_date, end_date).to_frame()


def download_sp500_history(
    *,
    start_date: str | None = None,
    end_date: str | None = None,
) -> pd.DataFrame:
    """Download daily S&P 500 close levels as a ``value`` column."""
    series = _download_sp500_closes(start_date, end_date)
    return series.rename("value").to_frame()


def backtest_sp500_to_csv(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["date", "value"])

    out = df.copy()
    if "value" not in out.columns and len(out.columns) == 1:
        out = out.rename(columns={out.columns[0]: "value"})
    out = out.reset_index()
    date_col = "date" if "date" in out.columns else out.columns[0]
    out = out.rename(columns={date_col: "date"})
    out["date"] = pd.to_datetime(out["date"]).dt.strftime("%Y-%m-%d")
    return out[["date", "value"]].sort_values("date")


def save_backtest_sp500_csv(
    df: pd.DataFrame,
    path: Path | None = None,
) -> Path:
    output_path = path or DEFAULT_BACKTEST_SP500_PATH
    output_path.parent.mkdir(parents=True, exist_ok=True)
    backtest_sp500_to_csv(df).to_csv(output_path, index=False)
    return output_path


def load_backtest_sp500_csv(
    path: Path | None = None,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
) -> pd.DataFrame:
    """Load stored backtest SP500 levels as a ``SP500``-column DataFrame."""
    csv_path = path or DEFAULT_BACKTEST_SP500_PATH
    if not csv_path.exists():
        raise FileNotFoundError(
            f"Backtest SP500 file not found: {csv_path}. "
            "Run `uv run python job/download_sp500.py` first."
        )

    df = pd.read_csv(csv_path, parse_dates=["date"]).set_index("date").sort_index()
    df = df.rename(columns={"value": "SP500"})
    if start_date is not None:
        df = df.loc[df.index >= pd.Timestamp(start_date)]
    if end_date is not None:
        df = df.loc[df.index <= pd.Timestamp(end_date)]
    return df[["SP500"]]


def download_and_store_backtest_sp500(
    *,
    start_date: str | None = None,
    end_date: str | None = None,
    path: Path | None = None,
) -> Path:
    history = download_sp500_history(start_date=start_date, end_date=end_date)
    output_path = save_backtest_sp500_csv(history, path)
    print(
        f"Saved {len(history)} SP500 observations to {output_path} "
        f"({history.index.min().date()} to {history.index.max().date()})."
    )
    return output_path
