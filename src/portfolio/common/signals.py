from functools import reduce

import pandas as pd

from portfolio.common.macro_constants import (
    ALERT_FINANCIAL_STRESS,
    ALERT_INVERTED_CURVE,
    ALERT_SAHM,
    FINANCIAL_STRESS_INDEX,
    SAHM_VALUE,
    YIELD_SPREAD_10Y3M,
)
from portfolio.common.macro_signals import MacroSignalFn
from portfolio.datasources.fred import download_fred_data, init_client


def compute_signals(
    fred_api_key: str,
    fred_series: list[tuple[str, str]],
    macro_signals: list[MacroSignalFn],
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    data_df = download_data(fred_api_key, fred_series, start_date, end_date)
    macro_df = calculate_macro_signals(data_df, macro_signals)
    market_df = calculate_market_signals(macro_df)
    print_current_signals(market_df)
    return market_df


def download_data(
    fred_api_key: str | None,
    fred_series: list[tuple[str, str]],
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    fred = init_client(fred_api_key)

    macro_series_data = [
        download_fred_data(fred, series_id, column_name, start_date, end_date)
        for series_id, column_name in fred_series
    ]

    # 2. Synchronize calendars (We unify everything using S&P 500 trading days)
    sp500 = download_fred_data(fred, "SP500", "SP500", start_date, end_date)

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
    df["SP500_Death_Cross"] = (
        df["SP500_SMA50"].shift(1) >= df["SP500_SMA200"].shift(1)
    ) & (df["SP500_SMA50"] < df["SP500_SMA200"])
    # Active state while SMA50 remains below SMA200
    df["SP500_Death_Cross_Active"] = df["SP500_SMA50"] < df["SP500_SMA200"]

    # Confirmed death cross: SMA50 is 5% or more below SMA200
    df["SP500_Confirmed_Death_Cross"] = df["SP500_SMA50"] <= (df["SP500_SMA200"] * 0.95)

    return df


def print_current_signals(df: pd.DataFrame):
    if df.empty:
        return

    row = df.iloc[-1]

    print("\nMacro signals")
    print(
        f"1. Curve Inversion (10Y-3M): {float(row[YIELD_SPREAD_10Y3M]):.2f}% -> {row[ALERT_INVERTED_CURVE]}"
    )
    print(
        f"2. Sahm Rule (Employment): {float(row[SAHM_VALUE]):.2f}% -> {row[ALERT_SAHM]}"
    )
    print(
        f"3. Financial Stress Index: {float(row[FINANCIAL_STRESS_INDEX]):.2f} -> {row[ALERT_FINANCIAL_STRESS]}"
    )

    print("\nMarket signals")
    print(f"4. SP500 Death Cross: {row['SP500_Death_Cross_Active']}")
    print(f"5. SP500 Confirmed Death Cross: {row['SP500_Confirmed_Death_Cross']}")
