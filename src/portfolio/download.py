import json

import pandas as pd
import requests
from urllib.parse import urlencode

BASE_URL = "http://tools.morningstar.es/api/rest.svc/timeseries_price/2nhcdckzon"


def _compute_params(fund_id: str, currency: str, start: str, end: str) -> dict[str, str]:
    return {
        "id": f"{fund_id}]2]1]",
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


def download_price_data(fund_id: str, currency: str, start: str, end: str, timeout: int = 30) -> pd.DataFrame:
    """Download Morningstar time series data and parse it into a pandas DataFrame."""
    params = _compute_params(fund_id, currency, start, end)
    url = BASE_URL + "?" + urlencode(params)

    try:
        response = requests.get(url, timeout=timeout)
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


if __name__ == "__main__":
    print(download_price_data("0P0001CC3N", "EUR", "2020-01-01", "2020-04-30"))