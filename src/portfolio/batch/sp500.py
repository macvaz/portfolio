"""Download S&P 500 index history from Morningstar."""

from __future__ import annotations

from datetime import date

import pandas as pd

from portfolio.datasource.morningstar import download_navs

# Morningstar security ID for the S&P 500 price index (long-term daily history).
SP500_SECURITY_ID = "XIUSA000OA"


def _download_sp500_closes(
    start_date: str | None = None,
    end_date: str | None = None,
) -> pd.Series:
    start = start_date or "1950-01-01"
    end = end_date or date.today().isoformat()
    history = download_navs(
        fund_id=SP500_SECURITY_ID,
        start=start,
        end=end,
        currency="USD",
    )
    if history.empty or "value" not in history.columns:
        return pd.Series(dtype=float, name="SP500")

    close = history["value"].copy()
    close.name = "SP500"
    close.index = pd.to_datetime(close.index).tz_localize(None).normalize()
    return close.sort_index()


def download_sp500(
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    """Download daily S&P 500 close levels for the signals pipeline."""
    return _download_sp500_closes(start_date, end_date).to_frame()
