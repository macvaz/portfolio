"""
Morningstar fund lookup and NAV downloads.

Public API:
- import_isins: look up ISIN(s) on Morningstar and persist fund metadata
- download_navs: download NAV time series for a fund or portfolio
"""

import json
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, Optional

import pandas as pd
import requests

from portfolio.api.database import get_fund, list_funds, save_fund

MORNINGSTAR_FUND_QUOTE_URL = (
    "https://global.morningstar.com/es/inversiones/fondos/{performance_id}/cotizacion"
)
MORNINGSTAR_ETF_QUOTE_URL = (
    "https://global.morningstar.com/es/inversiones/etfs/{performance_id}/cotizacion"
)
BASE_URL = "http://tools.morningstar.es/api/rest.svc/timeseries_price/2nhcdckzon"
MS_SERIES_SUFFIX = "]2]1]"

__all__ = ["import_isins", "download_navs", "morningstar_quote_url", "parse_morningstar_search"]


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


def _has_isin_nav_data(
    isin: str, currency: str = "EUR", timeout: int = 15
) -> bool:
    end = date.today()
    start = end - timedelta(days=30)
    params = _compute_params(isin, currency, start.isoformat(), end.isoformat())
    try:
        response = requests.get(BASE_URL, params=params, timeout=timeout)
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError):
        return False
    return isinstance(payload, list) and len(payload) > 0


def _search_by_isin(isin: str) -> Dict | None:
    """Look up a single ISIN using Morningstar's tools API."""
    print(f"[*] Looking up ISIN: {isin}")
    if not _has_isin_nav_data(isin):
        print(f"[-] No Morningstar NAV data found for ISIN {isin}")
        print(
            "[-] Import the fund via the add-fund screen using JSON "
            "from the Morningstar legacy-search URL in your browser."
        )
        return None

    print(f"[+] Resolved {isin}")
    return {
        "security_id": isin,
        "performance_id": None,
        "universe": None,
        "name": isin,
        "isin": isin,
    }


def _resolve_fund_by_isin(isin: str, db_path: Path | None = None) -> Dict | None:
    """Return fund metadata for an ISIN, using the database when available."""
    cached = get_fund(isin, db_path)
    if cached is not None:
        if cached.get("performance_id") and cached.get("universe"):
            return {
                "security_id": cached["security_id"],
                "performance_id": cached["performance_id"],
                "universe": cached["universe"],
                "name": cached["name"],
                "isin": isin,
            }

        fund = _search_by_isin(isin)
        if fund is None:
            return {
                "security_id": cached["security_id"],
                "performance_id": cached.get("performance_id"),
                "universe": cached.get("universe"),
                "name": cached["name"],
                "isin": isin,
            }

        save_fund(
            isin,
            cached["name"],
            cached["security_id"],
            fund.get("performance_id") or cached.get("performance_id"),
            fund.get("universe") or cached.get("universe"),
            db_path,
        )
        return {
            "security_id": cached["security_id"],
            "performance_id": fund.get("performance_id")
            or cached.get("performance_id"),
            "universe": fund.get("universe") or cached.get("universe"),
            "name": cached["name"],
            "isin": isin,
        }

    fund = _search_by_isin(isin)
    if fund is None:
        return None

    save_fund(
        isin,
        fund["name"],
        fund["security_id"],
        fund["performance_id"],
        fund.get("universe"),
        db_path,
    )
    return fund


def _backfill_performance_ids(db_path: Path | None = None) -> int:
    """Fetch and store Morningstar performance IDs for funds missing them."""
    updated = 0
    for fund in list_funds(db_path):
        if fund.get("performance_id") and fund.get("universe"):
            continue
        resolved = _resolve_fund_by_isin(fund["isin"], db_path)
        if resolved and resolved.get("performance_id"):
            updated += 1
    return updated


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


def _extract_records(data: list[list[float | int]]) -> list[dict[str, float | int]]:
    """Convert a list of [timestamp, value] rows into record dicts."""
    return [{"timestamp": int(timestamp), "value": value} for timestamp, value in data]


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


def _download_fund_navs(
    fund_id: str, currency: str, start: str, end: str, timeout: int = 30
) -> pd.DataFrame:
    """Download Morningstar time series data and parse it into a pandas DataFrame."""
    params = _compute_params(fund_id, currency, start, end)

    try:
        response = requests.get(BASE_URL, params=params, timeout=timeout)
        response.raise_for_status()
    except requests.RequestException as exc:
        print(f"Error downloading data from Morningstar: {exc}")
        return pd.DataFrame()

    try:
        payload = response.json()
    except ValueError:
        try:
            payload = json.loads(response.text)
        except ValueError:
            print("Received non-JSON response from Morningstar")
            return pd.DataFrame()

    records = _extract_records(payload)
    if records is None:
        print("No tabular data found in Morningstar response")
        return pd.DataFrame()

    df = pd.json_normalize(records)
    return _normalize_dataframe(df)


###################################
# Main morningstar public methods
###################################


def import_isins(
    isins: str | list[str] | None = None,
    *,
    db_path: Path | None = None,
) -> Dict | list[Dict | None] | int:
    """Import fund metadata from Morningstar.

    Pass a single ISIN to look up and persist one fund (returns dict or None).
    Pass a list to import multiple (returns a list in the same order).
    Pass None to backfill performance IDs for all funds in the database
    (returns the number of funds updated).
    """
    if isins is None:
        return _backfill_performance_ids(db_path)
    if isinstance(isins, str):
        return _resolve_fund_by_isin(isins, db_path)
    return [_resolve_fund_by_isin(isin, db_path) for isin in isins]


def download_navs(
    start: str,
    end: str,
    *,
    fund_id: str | None = None,
    portfolio: dict[str, float] | None = None,
    currency: str = "EUR",
    db_path: Path | None = None,
    timeout: int = 30,
) -> pd.DataFrame:
    """Download NAV time series for a fund or weighted portfolio."""
    if fund_id is not None:
        return _download_fund_navs(fund_id, currency, start, end, timeout)

    if portfolio is None:
        raise ValueError("Either fund_id or portfolio must be provided")

    navs_df = pd.DataFrame()
    for isin, weight in portfolio.items():
        fund = _resolve_fund_by_isin(isin, db_path)
        if fund is None:
            print(f"No fund found for ISIN: {isin}")
            continue
        fund_data = _download_fund_navs(
            fund["security_id"], currency, start, end, timeout
        )
        if fund_data.empty:
            print(f"No price data for ISIN: {isin}")
            continue
        navs_df[isin] = fund_data["value"]
        print(f"{isin} ({weight:.0%}): {fund['name']}")
    return navs_df


def morningstar_quote_url(
    performance_id: str | None,
    universe: str | None = None,
) -> str | None:
    """Build the Morningstar quote page URL for a fund or ETF performance ID."""
    if not performance_id:
        return None
    if universe == "FE":
        return MORNINGSTAR_ETF_QUOTE_URL.format(performance_id=performance_id)
    return MORNINGSTAR_FUND_QUOTE_URL.format(performance_id=performance_id)
