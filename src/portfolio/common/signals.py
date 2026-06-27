from functools import reduce
from pathlib import Path

import pandas as pd

from portfolio.common.macro_constants import (
    FINANCIAL_STRESS,
    FINANCIAL_STRESS_INDEX,
    INVERTED_CURVE,
    SAHM_VALUE,
    SP500_CONFIRMED_DEATH_CROSS,
    SP500_DEATH_CROSS,
    SP500_DEATH_CROSS_ACTIVE,
    SP500_SMA_RATIO,
    YIELD_SPREAD_10Y3M,
)
from portfolio.common.macro_signals import MacroSignalFn
from portfolio.common.series import DEFAULT_SERIES_DIR, save_series_csv
from portfolio.datasources.fred import download_fred_data, init_client


def compute_signals(
    fred_api_key: str | None,
    fred_series: list[tuple[str, str]],
    macro_signals: list[MacroSignalFn],
    start_date: str,
    end_date: str,
    series_dir: Path | None = None,
) -> pd.DataFrame:
    data_df = download_data(
        fred_api_key, fred_series, start_date, end_date, series_dir=series_dir
    )
    macro_df = calculate_macro_signals(data_df, macro_signals)
    market_df = calculate_market_signals(macro_df)
    print_current_signals(market_df)
    return market_df


def download_data(
    fred_api_key: str | None,
    fred_series: list[tuple[str, str]],
    start_date: str,
    end_date: str,
    series_dir: Path | None = None,
) -> pd.DataFrame:
    fred = init_client(fred_api_key)
    root = series_dir or DEFAULT_SERIES_DIR

    macro_series_data = []
    for series_id, column_name in fred_series:
        series_df = download_fred_data(
            fred, series_id, column_name, start_date, end_date
        )
        save_series_csv(
            series_id, series_df, column_name=column_name, series_dir=root
        )
        macro_series_data.append(series_df)

    # 2. Synchronize calendars (We unify everything using S&P 500 trading days)
    sp500 = download_fred_data(fred, "SP500", "SP500", start_date, end_date)
    save_series_csv("SP500", sp500, column_name="SP500", series_dir=root)

    # Create the master DataFrame indexed with actual market days
    df = pd.DataFrame(index=sp500.index)

    # Merge dataframes using their dates (indices)
    df = df.join(macro_series_data, how="left")

    # Forward fill the gaps (monthly unemployment or weekly stress data
    # remains constant on trading days until a new data point is published)
    df.ffill(inplace=True)
    df.bfill(inplace=True)  # Backward fill in case a series started slightly later

    df["SP500"] = sp500

    return df


def calculate_macro_signals(
    df: pd.DataFrame,
    macro_signals: list[MacroSignalFn],
) -> pd.DataFrame:
    return reduce(lambda current, signal_fn: signal_fn(current), macro_signals, df)


def calculate_market_signals(df: pd.DataFrame) -> pd.DataFrame:
    df["SP500_SMA50"] = df["SP500"].rolling(window=50, min_periods=1).mean()
    df["SP500_SMA200"] = df["SP500"].rolling(window=200, min_periods=1).mean()

    # Death cross event: SMA50 crosses below SMA200 (from yesterday to today)
    df[SP500_DEATH_CROSS] = (
        df["SP500_SMA50"].shift(1) >= df["SP500_SMA200"].shift(1)
    ) & (df["SP500_SMA50"] < df["SP500_SMA200"])
    # Active state while SMA50 remains below SMA200
    df[SP500_DEATH_CROSS_ACTIVE] = df["SP500_SMA50"] < df["SP500_SMA200"]

    # Confirmed death cross: SMA50 is 5% or more below SMA200
    df[SP500_CONFIRMED_DEATH_CROSS] = df["SP500_SMA50"] <= (
        df["SP500_SMA200"] * 0.95
    )
    df[SP500_SMA_RATIO] = df["SP500_SMA50"] / df["SP500_SMA200"]

    return df


def print_current_signals(df: pd.DataFrame):
    if df.empty:
        return

    row = df.iloc[-1]

    print("\nMacro signals")
    print(
        f"1. Curve Inversion (10Y-3M): {float(row[YIELD_SPREAD_10Y3M]):.2f}% -> {row[INVERTED_CURVE]}"
    )
    print(
        f"2. Sahm Rule (Employment): {float(row[SAHM_VALUE]):.2f}% -> {row[SAHM_VALUE]}"
    )
    print(
        f"3. Financial Stress Index: {float(row[FINANCIAL_STRESS_INDEX]):.2f} -> {row[FINANCIAL_STRESS]}"
    )

    print("\nMarket signals")
    print(f"4. SP500 Death Cross: {row[SP500_DEATH_CROSS_ACTIVE]}")
    print(f"5. SP500 Confirmed Death Cross: {row[SP500_CONFIRMED_DEATH_CROSS]}")
