#!/usr/bin/env python3
"""Standalone Morningstar category exploration script.

Steps:
1. Fetch fund ``security_details`` and build category → security_id mapping
   (``_CategoryId`` / category name on each fund).
2. Pick one security_id and download its price series.
3. Report performance for 1w / 2w / 1m (trading-day windows), plus Morningstar
   trailing W1 / M1 when present in the details payload.
4. Pull SAL performance/chart (``benchmarkId=mstarorcat``) and report
   **monthly category-wide returns** from ``graphData.category``.

Morningstar HTTP calls must run inside the portfolio Docker container.
From the host, use::

  ./bin/category_test.sh
  ./bin/category_test.sh --security-id F0GBR04VSJ
  ./bin/category_test.sh --isin ES0182527038
  ./bin/category_test.sh --token "$MORNINGSTAR_ACCESS_TOKEN"
  ./bin/category_test.sh --chart-json data/fixtures/performance_chart_category_sample.json

Live SAL chart calls need a browser ``access_token`` (env
``MORNINGSTAR_ACCESS_TOKEN`` or ``--token``). Without it, pass ``--chart-json``
or rely on the bundled sample fixture for the category step.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import urlencode

import requests

DETAILS_URL = "https://lt.morningstar.com/api/rest.svc/security_details/t92wz0sj7c"
TIMESERIES_URL = "https://lt.morningstar.com/api/rest.svc/timeseries_price/t92wz0sj7c"
SAL_CHART_URL = (
    "https://api-global.morningstar.com/sal-service/v1/fund/data/performance/chart"
)
MS_SERIES_SUFFIX = "]2]1]"

# Same trading-day windows as portfolio metrics.
WINDOW_DAYS = {"1w": 5, "2w": 10, "1m": 21}

DEFAULT_HEADERS = {
    "User-Agent": "portfolio-category-test/1.0",
    "Accept": "*/*",
}

FIXTURE_PATH = Path(__file__).resolve().parent / "data" / "fixtures" / "fund.json"
CHART_SAMPLE_PATH = (
    Path(__file__).resolve().parent
    / "data"
    / "fixtures"
    / "performance_chart_category_sample.json"
)
CONTAINER_NAME = os.environ.get("PORTFOLIO_CONTAINER", "portfolio")
TOKEN_ENV = "MORNINGSTAR_ACCESS_TOKEN"


def running_in_docker() -> bool:
    if Path("/.dockerenv").exists():
        return True
    try:
        cgroup = Path("/proc/1/cgroup").read_text(encoding="utf-8")
    except OSError:
        return False
    return "docker" in cgroup or "containerd" in cgroup


def ensure_docker() -> None:
    """Re-exec inside the portfolio container when started on the host."""
    if running_in_docker():
        return
    if os.environ.get("CATEGORY_TEST_ALLOW_HOST") == "1":
        print(
            "WARNING: running Morningstar calls on the host "
            "(CATEGORY_TEST_ALLOW_HOST=1).",
            file=sys.stderr,
        )
        return

    script = "category_test.py"
    # Strip --token from argv and pass via env so the JWT is not on the
    # docker exec command line.
    forwarded: list[str] = []
    token_from_cli: str | None = None
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--token" and i + 1 < len(args):
            token_from_cli = args[i + 1]
            i += 2
            continue
        if arg.startswith("--token="):
            token_from_cli = arg.split("=", 1)[1]
            i += 1
            continue
        forwarded.append(arg)
        i += 1

    env_pass = token_from_cli or os.environ.get(TOKEN_ENV)
    cmd = ["docker", "exec", "-i"]
    if env_pass:
        cmd.extend(["-e", f"{TOKEN_ENV}={env_pass}"])
    cmd.extend([CONTAINER_NAME, "python", script, *forwarded])
    print(f"Re-executing inside Docker: docker exec … python {script} …", file=sys.stderr)
    try:
        completed = subprocess.run(cmd, check=False)
    except FileNotFoundError as exc:
        raise SystemExit(
            "docker not found. Start the portfolio container and use "
            "./bin/category_test.sh"
        ) from exc
    raise SystemExit(completed.returncode)


def _get(url: str, params: dict, timeout: int = 45) -> requests.Response:
    response = requests.get(url, params=params, headers=DEFAULT_HEADERS, timeout=timeout)
    response.raise_for_status()
    return response


def fetch_security_details(security_id: str) -> str:
    """Return raw Morningstar security_details XML/JSON text."""
    response = _get(
        DETAILS_URL,
        {"id": security_id, "idtype": "Morningstar", "outputType": "JSON"},
    )
    if not response.text.strip():
        raise RuntimeError(f"Empty security_details response for {security_id!r}")
    return response.text


def parse_category(details_xml: str) -> tuple[str | None, str | None]:
    """Extract (category_id, category_name) from a security_details payload."""
    match = re.search(r'_CategoryId="([^"]+)"', details_xml)
    category_id = match.group(1) if match else None

    category_name = None
    if category_id:
        named = re.search(
            rf'<Category _Id="{re.escape(category_id)}">\s*([^<\n]+)\s*</Category>',
            details_xml,
        )
        if named:
            category_name = named.group(1).strip()
    if not category_name:
        fallback = re.search(r"<CategoryName>\s*([^<\n]+)\s*</CategoryName>", details_xml)
        if fallback:
            category_name = fallback.group(1).strip()
    return category_id, category_name


def parse_trailing_returns(details_xml: str, currency: str = "EUR") -> dict[str, float]:
    """Read Morningstar trailing ReturnDetail values (e.g. W1, M1)."""
    # Prefer type 1000 (total return style), then 3000 (often has W1).
    blocks: list[str] = []
    for perf_type in ("1000", "3000"):
        pattern = (
            rf'<TrailingPerformance Type="{perf_type}" _CurrencyId="{currency}">'
            rf"(.*?)</TrailingPerformance>"
        )
        blocks.extend(re.findall(pattern, details_xml, flags=re.S))

    out: dict[str, float] = {}
    for block in blocks:
        for period, value in re.findall(
            r'<ReturnDetail TimePeriod="([^"]+)">\s*<Value>([^<]+)</Value>',
            block,
        ):
            if period in out:
                continue
            try:
                out[period] = float(value)
            except ValueError:
                continue
    return out


def fetch_price_series(
    security_id: str,
    *,
    currency: str = "EUR",
    lookback_days: int = 120,
) -> list[tuple[date, float]]:
    """Download daily prices as (date, value), oldest → newest."""
    end = date.today()
    start = end - timedelta(days=lookback_days)
    params = {
        "id": f"{security_id}{MS_SERIES_SUFFIX}",
        "currencyId": currency,
        "idtype": "Morningstar",
        "frequency": "daily",
        "startDate": start.isoformat(),
        "endDate": end.isoformat(),
        "performanceType": "",
        "outputType": "COMPACTJSON",
    }
    response = _get(TIMESERIES_URL, params)
    payload = response.json()
    if not isinstance(payload, list) or not payload:
        raise RuntimeError(
            f"No price rows for {security_id!r} "
            f"({TIMESERIES_URL}?{urlencode(params)})"
        )

    points: list[tuple[date, float]] = []
    for row in payload:
        if not isinstance(row, (list, tuple)) or len(row) < 2:
            continue
        ts_ms, value = row[0], row[1]
        points.append((date.fromtimestamp(int(ts_ms) / 1000), float(value)))
    points.sort(key=lambda item: item[0])
    return points


def period_return(prices: list[tuple[date, float]], trading_days: int) -> float | None:
    """Compounded % return over the last ``trading_days`` steps."""
    if len(prices) < trading_days + 1:
        return None
    start_value = prices[-(trading_days + 1)][1]
    end_value = prices[-1][1]
    if start_value == 0:
        return None
    return (end_value / start_value - 1.0) * 100.0


def load_default_security_ids() -> list[dict]:
    """Load sample funds from the project fixture when present."""
    if not FIXTURE_PATH.exists():
        return [
            {
                "isin": None,
                "name": "Fidelity Fund",
                "security_id": "FOUSA00CFV",
            }
        ]
    rows = json.loads(FIXTURE_PATH.read_text())
    return [
        {
            "isin": row.get("isin"),
            "name": row.get("name"),
            "security_id": row.get("fund_id"),
        }
        for row in rows
        if row.get("fund_id")
    ]


def build_category_mapping(
    funds: list[dict],
    *,
    limit: int | None = None,
) -> dict[str, dict]:
    """
    Return mapping:
      category_id -> {
        "name": category_name,
        "security_ids": [{"security_id", "isin", "name"}, ...]
      }
    """
    selected = funds if limit is None else funds[:limit]
    mapping: dict[str, dict] = {}

    for fund in selected:
        security_id = fund["security_id"]
        print(f"  details {security_id} …", flush=True)
        details = fetch_security_details(security_id)
        category_id, category_name = parse_category(details)
        if not category_id:
            print(f"    ! no _CategoryId for {security_id}")
            continue

        entry = mapping.setdefault(
            category_id,
            {"name": category_name, "security_ids": []},
        )
        if category_name and not entry["name"]:
            entry["name"] = category_name
        entry["security_ids"].append(
            {
                "security_id": security_id,
                "isin": fund.get("isin"),
                "name": fund.get("name"),
            }
        )
        # stash details for the first security so we can reuse trailing returns
        if "details_xml" not in entry:
            entry["details_xml"] = details
            entry["sample_security_id"] = security_id

    return mapping


def print_mapping(mapping: dict[str, dict]) -> None:
    print("\n=== Category → security_id mapping ===")
    if not mapping:
        print("(empty)")
        return
    for category_id, entry in sorted(
        mapping.items(),
        key=lambda item: (item[1].get("name") or "", item[0]),
    ):
        label = entry.get("name") or "?"
        print(f"\n{label}")
        print(f"  category_id : {category_id}")
        for fund in entry["security_ids"]:
            isin = fund.get("isin") or "—"
            print(f"  security_id : {fund['security_id']}  ({isin})  {fund.get('name')}")


def print_performance(
    security_id: str,
    *,
    currency: str,
    details_xml: str | None = None,
) -> None:
    print(f"\n=== Performance for security_id={security_id} ({currency}) ===")
    prices = fetch_price_series(security_id, currency=currency)
    print(
        f"Price series: {len(prices)} points "
        f"({prices[0][0]} → {prices[-1][0]}, last={prices[-1][1]:.4f})"
    )

    print("\nComputed from daily prices (trading-day windows):")
    for label, days in WINDOW_DAYS.items():
        value = period_return(prices, days)
        if value is None:
            print(f"  {label:>3} ({days:>2}d): —  (not enough history)")
        else:
            print(f"  {label:>3} ({days:>2}d): {value:+.2f}%")

    xml = details_xml
    if xml is None:
        xml = fetch_security_details(security_id)
    trailing = parse_trailing_returns(xml, currency=currency)
    # Fall back to USD trailing if EUR block is sparse (common for US funds).
    if "W1" not in trailing and "M1" not in trailing and currency != "USD":
        trailing = parse_trailing_returns(xml, currency="USD")
        trail_ccy = "USD"
    else:
        trail_ccy = currency

    print(f"\nMorningstar trailing returns from security_details ({trail_ccy}):")
    for period, key in (("1w", "W1"), ("1m", "M1")):
        if key in trailing:
            print(f"  {period} ({key}): {trailing[key]:+.2f}%")
        else:
            print(f"  {period} ({key}): —")
    print("  2w: —  (no W2 field in security_details; use computed 2w above)")


def resolve_access_token(cli_token: str | None) -> str | None:
    """Prefer CLI token, then env var. Never log the value."""
    if cli_token and cli_token.strip():
        return cli_token.strip()
    env = os.environ.get(TOKEN_ENV, "").strip()
    return env or None


def fetch_performance_chart(
    share_class_id: str,
    *,
    access_token: str,
    locale: str = "es",
    client_id: str = "INTLCOM",
    version: str = "5.18.0",
) -> dict:
    """SAL chart including fund / category / index growth series."""
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
        **DEFAULT_HEADERS,
        "Accept": "application/json",
        "Origin": "https://global.morningstar.com",
        "Referer": "https://global.morningstar.com/",
    }
    response = requests.get(SAL_CHART_URL, params=params, headers=headers, timeout=60)
    if response.status_code == 401:
        raise RuntimeError(
            "SAL chart returned 401 Unauthorized — refresh "
            f"{TOKEN_ENV} / --token from a logged-in browser session."
        )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise RuntimeError("Unexpected SAL chart payload (expected object)")
    return payload


def load_chart_json(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"{path}: expected a JSON object")
    return payload


def parse_growth_series(payload: dict, key: str) -> list[tuple[date, float]]:
    """Parse graphData.<key> into sorted (date, value) points."""
    graph = payload.get("graphData") or {}
    rows = graph.get(key) or []
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


def series_period_returns(
    points: list[tuple[date, float]],
) -> list[tuple[date, date, float]]:
    """Consecutive growth-point returns: (start_date, end_date, pct)."""
    out: list[tuple[date, date, float]] = []
    for (d0, v0), (d1, v1) in zip(points, points[1:]):
        if v0 == 0:
            continue
        out.append((d0, d1, (v1 / v0 - 1.0) * 100.0))
    return out


def compounded_return(pcts: list[float]) -> float:
    factor = 1.0
    for pct in pcts:
        factor *= 1.0 + pct / 100.0
    return (factor - 1.0) * 100.0


def print_category_monthly_returns(
    payload: dict,
    *,
    source: str,
    months: int = 12,
) -> None:
    """Print monthly category returns from a SAL performance/chart payload."""
    category_name = payload.get("categoryName") or "?"
    as_of = (payload.get("asOfDate") or "")[:10] or "?"
    points = parse_growth_series(payload, "category")
    returns = series_period_returns(points)

    print("\n=== 3) Monthly category-wide returns (SAL chart) ===")
    print(f"Source        : {source}")
    print(f"Category      : {category_name}")
    print(f"As of         : {as_of}")
    print(f"Category pts  : {len(points)}  ({points[0][0]} → {points[-1][0]})" if points else "Category pts  : 0")

    if not returns:
        print("No category return intervals available.")
        return

    shown = returns[-months:] if months > 0 else returns
    print(f"\nLast {len(shown)} period return(s) from graphData.category:")
    for start, end, pct in shown:
        # Chart points are usually month-end; mid-month last point = MTD.
        tag = "  (partial / MTD)" if end.day < 28 else ""
        print(f"  {start} → {end}: {pct:+.2f}%{tag}")

    # Trailing windows over completed intervals (exclude current partial if any).
    completed = [r for r in returns if r[1].day >= 28]
    if not completed:
        completed = returns
    print("\nTrailing compounded category returns:")
    for label, n in (("1m", 1), ("3m", 3), ("6m", 6), ("12m", 12)):
        if len(completed) < n:
            print(f"  {label}: —  (need {n} intervals, have {len(completed)})")
            continue
        window = completed[-n:]
        total = compounded_return([pct for _, _, pct in window])
        print(
            f"  {label}: {total:+.2f}%  "
            f"({window[0][0]} → {window[-1][1]})"
        )


def print_category_step(
    *,
    share_class_id: str | None,
    access_token: str | None,
    chart_json: Path | None,
    months: int,
) -> None:
    if chart_json is not None:
        payload = load_chart_json(chart_json)
        print_category_monthly_returns(
            payload, source=f"file:{chart_json}", months=months
        )
        return

    if access_token and share_class_id:
        print(f"\nFetching SAL chart for shareClassId={share_class_id} …", flush=True)
        payload = fetch_performance_chart(share_class_id, access_token=access_token)
        print_category_monthly_returns(
            payload,
            source=f"SAL chart shareClassId={share_class_id}",
            months=months,
        )
        return

    if CHART_SAMPLE_PATH.exists():
        print(
            f"\nNo {TOKEN_ENV}/--token (or --chart-json); "
            f"using sample fixture {CHART_SAMPLE_PATH.name}.",
            file=sys.stderr,
        )
        payload = load_chart_json(CHART_SAMPLE_PATH)
        print_category_monthly_returns(
            payload, source=f"fixture:{CHART_SAMPLE_PATH.name}", months=months
        )
        return

    print(
        f"\nSkipping category monthly returns: set {TOKEN_ENV} / --token "
        "or pass --chart-json.",
        file=sys.stderr,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--security-id",
        help="Morningstar security_id / fund_id to inspect for performance",
    )
    parser.add_argument(
        "--isin",
        help="Pick the fixture fund with this ISIN for the performance step",
    )
    parser.add_argument(
        "--currency",
        default="EUR",
        help="Currency for price series / trailing returns (default: EUR)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=12,
        help="Max fixture funds to use when building the category map",
    )
    parser.add_argument(
        "--token",
        help=f"SAL access_token (prefer env {TOKEN_ENV}; do not commit tokens)",
    )
    parser.add_argument(
        "--chart-json",
        type=Path,
        help="Offline SAL performance/chart JSON (skips live token call)",
    )
    parser.add_argument(
        "--months",
        type=int,
        default=12,
        help="How many recent category period returns to print (default: 12)",
    )
    parser.add_argument(
        "--skip-fund-perf",
        action="store_true",
        help="Skip daily fund performance step (mapping + category only)",
    )
    return parser.parse_args()


def main() -> int:
    ensure_docker()
    args = parse_args()
    funds = load_default_security_ids()
    if not funds:
        print("No sample funds available.", file=sys.stderr)
        return 1

    print("=== 1) Category ↔ security_id mapping ===")
    print(f"Fetching security_details for up to {args.limit} funds…")
    mapping = build_category_mapping(funds, limit=args.limit)
    print_mapping(mapping)

    # Choose security_id for performance / SAL chart proxy.
    security_id = args.security_id
    details_xml = None
    if args.isin and not security_id:
        wanted = args.isin.upper()
        match = next((f for f in funds if (f.get("isin") or "").upper() == wanted), None)
        if not match:
            print(f"ISIN {wanted} not found in fixture funds.", file=sys.stderr)
            return 1
        security_id = match["security_id"]

    if not security_id:
        # Prefer a security that already appeared in the mapping.
        for entry in mapping.values():
            if entry.get("sample_security_id"):
                security_id = entry["sample_security_id"]
                details_xml = entry.get("details_xml")
                break
        if not security_id:
            security_id = funds[0]["security_id"]

    if not args.skip_fund_perf:
        print("\n=== 2) Performance for one security_id ===")
        print_performance(
            security_id, currency=args.currency.upper(), details_xml=details_xml
        )

    token = resolve_access_token(args.token)
    print_category_step(
        share_class_id=security_id,
        access_token=token,
        chart_json=args.chart_json,
        months=args.months,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
