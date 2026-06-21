"""
Morningstar fund lookup and NAV downloads.

Public API:
- import_isins: look up ISIN(s) on Morningstar and persist fund metadata
- download_navs: download NAV time series for a fund or portfolio
"""

import asyncio
import json
import re
from pathlib import Path
from typing import Dict, Optional

import pandas as pd
import requests
from playwright.async_api import async_playwright

from portfolio.api.database import get_fund, list_funds, save_fund

DOMAIN = "https://global.morningstar.com"
MORNINGSTAR_FUND_QUOTE_URL = (
    "https://global.morningstar.com/es/inversiones/fondos/{performance_id}/cotizacion"
)
MORNINGSTAR_ETF_QUOTE_URL = (
    "https://global.morningstar.com/es/inversiones/etfs/{performance_id}/cotizacion"
)
BASE_URL = "http://tools.morningstar.es/api/rest.svc/timeseries_price/2nhcdckzon"
MS_SERIES_SUFFIX = "]2]1]"

__all__ = ["import_isins", "download_navs", "morningstar_quote_url"]

async def _search_isin_async(isin: str) -> Optional[Dict]:
    """Search for a fund by ISIN using Morningstar's API with Playwright."""
    query = f"((isin+~%3D+%22{isin}%22))"
    url = f"{DOMAIN}/api/v1/es/legacy-search/securities?fields=isin,name&query={query}&sort=_score"

    async with async_playwright() as p:
        print("[*] Launching headless browser (Playwright)...")
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            ignore_https_errors=True,
        )

        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => false,
            });
        """)

        page = await context.new_page()
        await page.set_extra_http_headers(
            {
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Referer": "https://global.morningstar.com/",
                "Origin": "https://global.morningstar.com",
            }
        )

        try:
            print(f"[*] Visiting domain: {DOMAIN}")
            await page.goto(DOMAIN, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(2000)

            print(f"[*] Searching for ISIN: {isin}")
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(1000)

            page_content = await page.content()

            try:
                data = json.loads(page_content)
                print(f"[+] Successfully retrieved search results for {isin}")
                return data
            except json.JSONDecodeError:
                match = re.search(r"<pre[^>]*>({.*})</pre>", page_content, re.DOTALL)
                if match:
                    data = json.loads(match.group(1))
                    print(f"[+] Successfully retrieved search results for {isin}")
                    return data

                json_match = re.search(r"({.*})", page_content, re.DOTALL)
                if json_match:
                    try:
                        data = json.loads(json_match.group(1))
                        print(f"[+] Successfully retrieved search results for {isin}")
                        return data
                    except Exception:
                        pass

                print(f"[-] Could not extract search results for {isin}")
                return None

        except Exception as e:
            print(f"[-] Error searching for ISIN {isin}: {e}")
            return None

        finally:
            await context.close()
            await browser.close()


def _search_by_isin(isin: str) -> Dict | None:
    """Look up a single ISIN on Morningstar."""
    response = asyncio.run(_search_isin_async(isin))
    if response is None:
        return None
    results = response["results"][0]
    security_name = results["fields"]["name"]["value"]
    security_id = results["meta"]["securityID"]
    performance_id = results["meta"]["performanceID"]
    universe = results["meta"].get("universe")
    return {
        "security_id": security_id,
        "performance_id": performance_id,
        "universe": universe,
        "name": security_name,
        "isin": isin,
    }


def _resolve_fund_by_isin(
    isin: str, db_path: Path | None = None
) -> Dict | None:
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
            "performance_id": fund.get("performance_id") or cached.get("performance_id"),
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
        fund_data = _download_fund_navs(fund["security_id"], currency, start, end, timeout)
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
