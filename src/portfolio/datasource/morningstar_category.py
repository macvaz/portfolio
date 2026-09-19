"""Morningstar SAL category average chart downloads."""

from __future__ import annotations

from datetime import date, datetime

import requests

from portfolio.datasource.errors import DownloadError

SAL_CHART_URL = (
    "https://api-global.morningstar.com/sal-service/v1/fund/data/performance/chart"
)

__all__ = [
    "fetch_performance_chart",
    "parse_category_price_points",
]


def fetch_performance_chart(
    share_class_id: str,
    *,
    access_token: str,
    locale: str = "es",
    client_id: str = "INTLCOM",
    version: str = "5.18.0",
) -> dict:
    """Download SAL performance/chart including category benchmark series."""
    params = {
        "shareClassId": share_class_id,
        "secExchangeList": "",
        "limitAge": "",
        "hideYTD": "false",
        "locale": locale,
        "clientId": client_id,
        "benchmarkId": "mstarorcat",
        "version": version,
        "access_token": access_token,
    }
    headers = {
        "User-Agent": "portfolio/1.0",
        "Accept": "application/json",
        "Origin": "https://global.morningstar.com",
        "Referer": "https://global.morningstar.com/",
    }
    try:
        response = requests.get(
            SAL_CHART_URL, params=params, headers=headers, timeout=60
        )
    except requests.RequestException as exc:
        raise DownloadError(f"Morningstar SAL chart request failed: {exc}") from exc

    if response.status_code == 401:
        raise DownloadError(
            "Morningstar SAL chart unauthorized — refresh the access token"
        )
    if not response.ok:
        raise DownloadError(
            f"Morningstar SAL chart HTTP {response.status_code}: {response.text[:200]}"
        )

    payload = response.json()
    if not isinstance(payload, dict):
        raise DownloadError("Unexpected SAL chart payload (expected object)")
    return payload


def parse_category_price_points(payload: dict) -> list[tuple[date, float]]:
    """Extract graphData.category as sorted (date, value) points."""
    graph = payload.get("graphData") or {}
    rows = graph.get("category") or []
    points: list[tuple[date, float]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        raw_date = row.get("date")
        raw_value = row.get("value")
        if raw_date is None or raw_value is None:
            continue
        try:
            d = datetime.strptime(str(raw_date)[:10], "%Y-%m-%d").date()
            v = float(raw_value)
        except (TypeError, ValueError):
            continue
        points.append((d, v))
    points.sort(key=lambda item: item[0])
    return points
