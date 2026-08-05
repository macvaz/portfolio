"""Shared market DataFrame construction for batch and macro health history."""

from pathlib import Path

import pandas as pd

from portfolio.common.health_check_descriptions import (
    load_health_check_description_fixture,
)
from portfolio.common.indexes import DEFAULT_INDEXES_DIR, load_index_csv
from portfolio.common.macro_constants import SP500_DEATH_CROSS
from portfolio.common.series import DEFAULT_SERIES_DIR, load_series_csv


def apply_macro_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Derive macro indicators (e.g. SP500 death cross) on a market DataFrame."""
    if "SP500" not in df.columns:
        return df
    sma50 = df["SP500"].rolling(window=50, min_periods=1).mean()
    sma200 = df["SP500"].rolling(window=200, min_periods=1).mean()
    df[SP500_DEATH_CROSS] = sma50 / sma200
    return df


def align_market_dataframe(
    sp500: pd.DataFrame | None,
    macro_frames: list[pd.DataFrame],
) -> pd.DataFrame:
    """Align macro columns onto the SP500 calendar (ffill only) when available."""
    macros = [frame for frame in macro_frames if frame is not None and not frame.empty]

    if sp500 is not None and not sp500.empty:
        df = pd.DataFrame(index=sp500.index)
        for frame in macros:
            df = df.join(frame, how="left")
        df.ffill(inplace=True)
        df["SP500"] = sp500["SP500"]
        return apply_macro_indicators(df)

    if not macros:
        return pd.DataFrame()

    df = macros[0]
    for frame in macros[1:]:
        df = df.join(frame, how="outer")
    df = df.sort_index()
    df.ffill(inplace=True)
    return apply_macro_indicators(df)


def load_market_dataframe(
    series_dir: Path | None = None,
    indexes_dir: Path | None = None,
) -> pd.DataFrame:
    """Load FRED series + SP500 CSVs and build the market DataFrame."""
    series_root = series_dir or DEFAULT_SERIES_DIR
    indexes_root = indexes_dir or DEFAULT_INDEXES_DIR
    fixture = load_health_check_description_fixture()

    macros: list[pd.DataFrame] = []
    for entry in fixture:
        if entry.get("source") != "fred" or not entry.get("series_id"):
            continue
        code = str(entry["code"])
        series_id = str(entry["series_id"])
        series = load_series_csv(series_id, series_root)
        if series.empty:
            continue
        macros.append(series.rename(columns={series_id: code}))

    sp500 = load_index_csv("SP500", indexes_root)
    if sp500.empty:
        sp500 = None

    return align_market_dataframe(sp500, macros)
