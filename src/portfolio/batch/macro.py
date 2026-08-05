"""Download FRED + SP500 series and compute macro health indicators."""

import logging
from pathlib import Path

import pandas as pd

from portfolio.batch.sp500 import download_sp500
from portfolio.common.health_check_descriptions import (
    HEALTH_CHECK_ROLE,
    is_health_check_active,
    load_health_check_description_fixture,
)
from portfolio.common.indexes import DEFAULT_INDEXES_DIR, save_index_csv
from portfolio.common.market import align_market_dataframe
from portfolio.common.series import DEFAULT_SERIES_DIR, save_series_csv
from portfolio.datasource.errors import DownloadError
from portfolio.datasource.fred import download_fred_data, init_client

logger = logging.getLogger(__name__)


def compute_macro(
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
    log_current_macro_health(market_df)
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
        logger.warning(
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
                logger.error("Failed %s: %s", series_id, exc)
                failures.append(str(exc))
                continue
            logger.info("Saved %s: %s", series_id, column_name)
            downloaded.append((series_id, column_name, series_df))
        logger.info(
            "Done. Saved %s of %s FRED series.",
            len(downloaded),
            len(fred_series),
        )
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

    logger.info("Downloading SP500 history from Morningstar")
    sp500 = download_sp500(start_date, end_date)
    if sp500.empty:
        raise DownloadError("SP500 download returned no observations")
    save_index_csv("SP500", sp500, column_name="SP500", indexes_dir=indexes_root)

    return align_market_dataframe(sp500, macro_series_data)


def log_current_macro_health(df: pd.DataFrame):
    if df.empty:
        return

    row = df.iloc[-1]
    logger.info("Macro health")
    for entry in load_health_check_description_fixture():
        code = str(entry["code"])
        if code not in row.index or pd.isna(row[code]):
            continue
        value = float(row[code])
        threshold = entry.get("threshold")
        operator = entry.get("operator")
        active = is_health_check_active(value, threshold, operator)
        role = entry.get("role") or HEALTH_CHECK_ROLE
        if active is None:
            logger.info("%s: %.2f (%s)", code, value, role)
        else:
            logger.info("%s: %.2f (active=%s)", code, value, active)
