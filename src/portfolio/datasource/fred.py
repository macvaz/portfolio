import types
import xml.etree.ElementTree as ET
from urllib.error import HTTPError
from urllib.request import urlopen

import pandas as pd
from fredapi import Fred

from portfolio.datasource.errors import DownloadError

FRED_DEPRECATED_SERIES_IDS = frozenset({"SP500"})


def _fred_http_error_detail(exc: HTTPError, body: bytes) -> str:
    """Build a useful message from a FRED HTTPError (fredapi often yields None)."""
    text = body.decode("utf-8", errors="replace").strip()
    message = None
    if body:
        try:
            root = ET.fromstring(body)
            message = root.get("message") or root.get("error_message")
            if not message:
                message = ET.tostring(root, encoding="unicode").strip()[:500] or None
        except ET.ParseError:
            message = text[:500] or None

    reason = f" {exc.reason}" if exc.reason else ""
    detail = message or text[:500] or "(empty error body)"
    return f"HTTP {exc.code}{reason}: {detail}"


def _fetch_fred_data(self: Fred, url: str):
    """Like fredapi.Fred.__fetch_data, but keep HTTP status/body on failure."""
    url += "&api_key=" + self.api_key
    try:
        response = urlopen(url)
        return ET.fromstring(response.read())
    except HTTPError as exc:
        body = exc.read() or b""
        raise ValueError(_fred_http_error_detail(exc, body)) from exc


def _format_fred_exception(exc: BaseException) -> str:
    msg = str(exc).strip()
    if msg and msg != "None":
        return msg
    return f"{type(exc).__name__} with empty message"


def init_client(api_key: str) -> Fred:
    client = Fred(api_key=api_key)
    # fredapi uses __fetch_data (name-mangled); replace so errors keep HTTP detail.
    client._Fred__fetch_data = types.MethodType(_fetch_fred_data, client)
    return client


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
            f"Failed to download FRED series {series_id!r}: {_format_fred_exception(exc)}"
        ) from exc

    if series is None or (hasattr(series, "empty") and series.empty):
        raise DownloadError(f"FRED series {series_id!r} returned no observations")

    df = pd.DataFrame(series, columns=[column_name])
    df.index = pd.to_datetime(df.index)
    if df.empty or df[column_name].isna().all():
        raise DownloadError(f"FRED series {series_id!r} returned no observations")
    return df
