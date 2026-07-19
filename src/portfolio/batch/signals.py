"""Download FRED + SP500 series and compute tactical market signals."""

from pathlib import Path

import pandas as pd

from portfolio.batch.sp500 import download_sp500
from portfolio.common.alert_descriptions import (
    is_alert_active,
    load_alert_description_fixture,
)
from portfolio.common.indexes import DEFAULT_INDEXES_DIR, save_index_csv
from portfolio.common.market import align_market_dataframe
from portfolio.common.series import DEFAULT_SERIES_DIR, save_series_csv
from portfolio.datasource.errors import DownloadError
from portfolio.datasource.fred import download_fred_data, init_client


def compute_signals(
    fred_api_key: str | None,
    fred_series: list[tuple[str, str]],
    start_date: str,
    end_date: str,
    series_dir: Path | None = None,
    indexes_dir: Path | None = None,
) -> pd.DataFrame:
    market_df = download_data(
        fred_api_key,
        fred_series,
        start_date,
        end_date,
        series_dir=series_dir,
        indexes_dir=indexes_dir,
    )
    print_current_signals(market_df)
    return market_df


def download_data(
    fred_api_key: str | None,
    fred_series: list[tuple[str, str]],
    start_date: str,
    end_date: str,
    series_dir: Path | None = None,
    indexes_dir: Path | None = None,
) -> pd.DataFrame:
    series_root = series_dir or DEFAULT_SERIES_DIR
    indexes_root = indexes_dir or DEFAULT_INDEXES_DIR

    macro_series_data: list[pd.DataFrame] = []
    if not fred_api_key:
        print(
            "FRED_API_KEY not set; skipping FRED series downloads. "
            "Continuing with SP500; existing series files are left unchanged."
        )
    else:
        fred = init_client(fred_api_key)
        downloaded: list[tuple[str, str, pd.DataFrame]] = []
        failures: list[str] = []
        for series_id, column_name in fred_series:
            try:
                series_df = download_fred_data(
                    fred, series_id, column_name, start_date, end_date
                )
            except DownloadError as exc:
                failures.append(str(exc))
                continue
            downloaded.append((series_id, column_name, series_df))
        if failures:
            raise DownloadError(
                "FRED download failed for "
                f"{len(failures)} series:\n- " + "\n- ".join(failures)
            )
        for series_id, column_name, series_df in downloaded:
            save_series_csv(
                series_id, series_df, column_name=column_name, series_dir=series_root
            )
            macro_series_data.append(series_df)

    print("Downloading SP500 history from Morningstar")
    sp500 = download_sp500(start_date, end_date)
    if sp500.empty:
        raise DownloadError("SP500 download returned no observations")
    save_index_csv("SP500", sp500, column_name="SP500", indexes_dir=indexes_root)

    return align_market_dataframe(sp500, macro_series_data)


def print_current_signals(df: pd.DataFrame):
    if df.empty:
        return

    row = df.iloc[-1]
    print("\nMacro health")
    for entry in load_alert_description_fixture():
        code = str(entry["code"])
        if code not in row.index or pd.isna(row[code]):
            continue
        value = float(row[code])
        threshold = entry.get("threshold")
        operator = entry.get("operator")
        active = is_alert_active(value, threshold, operator)
        role = entry.get("role") or "alert"
        if active is None:
            print(f"- {code}: {value:.2f} ({role})")
        else:
            print(f"- {code}: {value:.2f} (active={active})")
