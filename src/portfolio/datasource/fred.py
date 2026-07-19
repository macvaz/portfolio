import pandas as pd

from fredapi import Fred

from portfolio.datasource.errors import DownloadError

FRED_DEPRECATED_SERIES_IDS = frozenset({"SP500"})


def init_client(api_key: str) -> Fred:
    return Fred(api_key=api_key)


def download_fred_data(
    fred_client: Fred,
    series_id: str,
    column_name: str,
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    """Downloads a time series from FRED and returns a clean DataFrame."""
    if series_id in FRED_DEPRECATED_SERIES_IDS:
        raise ValueError(
            f"FRED series {series_id!r} is deprecated. "
            "Use portfolio.batch.sp500 for S&P 500 history."
        )
    try:
        series = fred_client.get_series(
            series_id, observation_start=start_date, observation_end=end_date
        )
    except Exception as exc:
        raise DownloadError(
            f"Failed to download FRED series {series_id!r}: {exc}"
        ) from exc

    if series is None or (hasattr(series, "empty") and series.empty):
        raise DownloadError(f"FRED series {series_id!r} returned no observations")

    df = pd.DataFrame(series, columns=[column_name])
    df.index = pd.to_datetime(df.index)
    if df.empty or df[column_name].isna().all():
        raise DownloadError(f"FRED series {series_id!r} returned no observations")
    return df
