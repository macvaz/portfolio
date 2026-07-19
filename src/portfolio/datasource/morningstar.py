"""
Morningstar fund lookup and NAV downloads.

Public API:
- parse_morningstar_search: parse legacy-search JSON into fund metadata
- download_navs: download NAV time series for a fund
- morningstar_quote_url: build a quote-page URL from a performance ID
"""

import json

import pandas as pd
import requests

from portfolio.datasource.errors import DownloadError

MORNINGSTAR_QUOTE_URL = (
    "https://global.morningstar.com/es/inversiones/{universe}/{performance_id}/cotizacion"
)
BASE_URL = "http://tools.morningstar.es/api/rest.svc/timeseries_price/2nhcdckzon"
MS_SERIES_SUFFIX = "]2]1]"

__all__ = ["download_navs", "morningstar_quote_url", "parse_morningstar_search"]

def _is_isin(identifier: str) -> bool:
    return len(identifier) == 12 and identifier.isalnum()


def parse_morningstar_search(payload: dict) -> dict:
    """Parse a Morningstar legacy-search JSON payload into fund metadata."""
    results = payload.get("results")
    if not results:
        raise ValueError("Morningstar response has no results")

    result = results[0]
    fields = result.get("fields") or {}
    meta = result.get("meta") or {}

    name = (fields.get("name") or {}).get("value")
    isin = (fields.get("isin") or {}).get("value")
    security_id = meta.get("securityID")
    performance_id = meta.get("performanceID")
    universe = meta.get("universe")

    missing = [
        label
        for label, value in [
            ("name", name),
            ("isin", isin),
            ("securityID", security_id),
            ("performanceID", performance_id),
        ]
        if not value
    ]
    if missing:
        raise ValueError(
            "Morningstar response is missing required fields: "
            + ", ".join(missing)
        )

    return {
        "isin": str(isin).upper(),
        "name": str(name),
        "security_id": str(security_id),
        "performance_id": str(performance_id),
        "universe": str(universe) if universe else None,
    }


def _compute_params(
    fund_id: str, currency: str, start: str, end: str
) -> dict[str, str]:
    """Build query params for the Morningstar timeseries endpoint."""
    if _is_isin(fund_id):
        return {
            "id": fund_id,
            "currencyId": currency,
            "idtype": "ISIN",
            "frequency": "daily",
            "startDate": start,
            "endDate": end,
            "performanceType": "",
            "outputType": "COMPACTJSON",
        }
    return {
        "id": f"{fund_id}{MS_SERIES_SUFFIX}",
        "currencyId": currency,
        "idtype": "Morningstar",
        "frequency": "daily",
        "startDate": start,
        "endDate": end,
        "performanceType": "",
        "outputType": "COMPACTJSON",
    }


def _extract_records(data: object) -> list[dict[str, float | int]]:
    """Convert a list of [timestamp, value] rows into record dicts."""
    if not isinstance(data, list):
        raise DownloadError(
            "Morningstar response is not a tabular list of [timestamp, value] rows"
        )
    if not data:
        raise DownloadError("Morningstar response contained no price rows")
    try:
        return [
            {"timestamp": int(timestamp), "value": value} for timestamp, value in data
        ]
    except (TypeError, ValueError) as exc:
        raise DownloadError(
            "Morningstar response rows are not [timestamp, value] pairs"
        ) from exc

def _normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize dates and index on the first recognized date column."""
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", errors="coerce")
        if df["timestamp"].notna().any():
            return df.set_index("timestamp")

    for date_col in ["date", "Date", "datetime", "DateTime", "Timestamp"]:
        if date_col in df.columns:
            df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
            if df[date_col].notna().any():
                return df.set_index(date_col)

    return df


def download_navs(
    fund_id: str,
    start: str,
    end: str,
    *,
    currency: str = "EUR",
    timeout: int = 30,
) -> pd.DataFrame:
    """Download Morningstar time series data and parse it into a pandas DataFrame."""
    params = _compute_params(fund_id, currency, start, end)

    try:
        response = requests.get(BASE_URL, params=params, timeout=timeout)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise DownloadError(
            f"Failed to download Morningstar series {fund_id!r}: {exc}"
        ) from exc

    try:
        payload = response.json()
    except ValueError:
        try:
            payload = json.loads(response.text)
        except ValueError as exc:
            raise DownloadError(
                f"Morningstar returned non-JSON for {fund_id!r}"
            ) from exc

    records = _extract_records(payload)
    df = pd.json_normalize(records)
    normalized = _normalize_dataframe(df)
    if normalized.empty:
        raise DownloadError(f"Morningstar series {fund_id!r} returned no observations")
    return normalized


def morningstar_quote_url(
    performance_id: str | None,
    universe: str | None = None,
) -> str | None:
    """Build the Morningstar quote page URL for a fund or ETF performance ID."""
    if not performance_id:
        return None
    return MORNINGSTAR_QUOTE_URL.format(
        performance_id=performance_id,
        universe="etfs" if universe == "FE" else "fondos",
    )
