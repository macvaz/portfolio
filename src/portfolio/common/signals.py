from pathlib import Path

import pandas as pd

from portfolio.common.macro_constants import (
    SP500_DEATH_CROSS,
    FINANCIAL_STRESS_INDEX,
    HIGH_YIELD_SPREAD,
    SAHM_RULE_INDICATOR,
    UNEMPLOYMENT_RATE,
    YIELD_SPREAD_10Y3M,
)
from portfolio.common.series import DEFAULT_SERIES_DIR, save_series_csv
from portfolio.common.alert_descriptions import (
    is_alert_active,
    load_alert_description_fixture,
)
from portfolio.datasources.fred import download_fred_data, init_client


def compute_signals(
    fred_api_key: str | None,
    fred_series: list[tuple[str, str]],
    start_date: str,
    end_date: str,
    series_dir: Path | None = None,
) -> pd.DataFrame:
    data_df = download_data(
        fred_api_key, fred_series, start_date, end_date, series_dir=series_dir
    )
    market_df = calculate_market_signals(data_df)
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

    sp500 = download_fred_data(fred, "SP500", "SP500", start_date, end_date)
    save_series_csv("SP500", sp500, column_name="SP500", series_dir=root)

    df = pd.DataFrame(index=sp500.index)
    df = df.join(macro_series_data, how="left")
    df.ffill(inplace=True)
    df.bfill(inplace=True)
    df["SP500"] = sp500

    return df


def calculate_market_signals(df: pd.DataFrame) -> pd.DataFrame:
    sma50 = df["SP500"].rolling(window=50, min_periods=1).mean()
    sma200 = df["SP500"].rolling(window=200, min_periods=1).mean()
    df[SP500_DEATH_CROSS] = sma50 / sma200
    return df


def print_current_signals(df: pd.DataFrame):
    if df.empty:
        return

    row = df.iloc[-1]
    print("\nTactical alerts")
    for entry in load_alert_description_fixture():
        code = str(entry["code"])
        if code not in row.index or pd.isna(row[code]):
            continue
        value = float(row[code])
        threshold = entry.get("threshold")
        operator = entry.get("operator")
        active = is_alert_active(value, threshold, operator)
        if active is None:
            print(f"- {code}: {value:.2f}")
        else:
            print(f"- {code}: {value:.2f} (active={active})")
