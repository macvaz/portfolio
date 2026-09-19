"""Batch download of Morningstar category monthly average data."""

from __future__ import annotations

import argparse
import logging
import os
import time
from pathlib import Path

from portfolio.datasource.errors import DownloadError
from portfolio.datasource.morningstar_category import (
    fetch_performance_chart,
    parse_category_price_points,
)
from portfolio.logging_config import configure_logging
from portfolio.storage.database import (
    DEFAULT_DB_PATH,
    init_db,
    list_categories,
    merge_category_monthly_data,
)

logger = logging.getLogger(__name__)

TOKEN_ENV = "MORNINGSTAR_ACCESS_TOKEN"
TOKEN_PATH_ENV = "MS_BEARER_TOKEN_PATH"


def resolve_access_token(cli_token: str | None = None) -> str | None:
    """
    Resolve the SAL bearer token.

    Order: CLI ``--token``, env ``MORNINGSTAR_ACCESS_TOKEN``, then the file
    pointed to by ``MS_BEARER_TOKEN_PATH`` (headless-browser convention).
    """
    if cli_token and cli_token.strip():
        return cli_token.strip()
    env_token = os.environ.get(TOKEN_ENV, "").strip()
    if env_token:
        return env_token
    token_path = os.environ.get(TOKEN_PATH_ENV, "").strip()
    if not token_path:
        return None
    path = Path(token_path)
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8").strip() or None


def download_category_monthly_data(
    access_token: str,
    *,
    db_path: Path = DEFAULT_DB_PATH,
    limit: int | None = None,
    asset_class: str | None = None,
    sleep_s: float = 0.15,
) -> dict:
    """
    Download SAL category average series for each catalog category with a fund_id.

    Stops immediately on unauthorized token errors.
    """
    token = access_token.strip()
    if not token:
        raise ValueError("access_token is required")

    init_db(db_path)
    categories = list_categories(db_path)
    if asset_class:
        wanted = asset_class.strip().lower()
        categories = [
            row for row in categories if (row.get("asset_class") or "").lower() == wanted
        ]
    categories = [row for row in categories if row.get("fund_id")]
    if limit is not None:
        categories = categories[: max(limit, 0)]

    ok = 0
    skipped = 0
    failed = 0
    errors: list[dict] = []

    logger.info(
        "Downloading monthly data for %s categor(y/ies)…",
        len(categories),
    )

    for index, row in enumerate(categories, start=1):
        category_id = row["category_id"]
        fund_id = row["fund_id"]
        name = row.get("name") or category_id
        logger.info(
            "[%s/%s] %s (%s) via %s",
            index,
            len(categories),
            name,
            category_id,
            fund_id,
        )
        try:
            payload = fetch_performance_chart(fund_id, access_token=token)
            points = parse_category_price_points(payload)
            if not points:
                skipped += 1
                logger.warning("No category series for %s", category_id)
                continue
            stored = merge_category_monthly_data(category_id, points, db_path=db_path)
            ok += 1
            logger.info(
                "Category %s: inserted=%s skipped=%s",
                category_id,
                stored["inserted"],
                stored["skipped"],
            )
        except DownloadError as exc:
            message = str(exc)
            if "unauthorized" in message.lower():
                logger.error("Token rejected; aborting batch: %s", message)
                raise
            failed += 1
            errors.append({"category_id": category_id, "error": message})
            logger.warning("Failed %s: %s", category_id, message)
        except Exception as exc:
            failed += 1
            errors.append({"category_id": category_id, "error": str(exc)})
            logger.exception("Unexpected failure for %s", category_id)

        if sleep_s > 0 and index < len(categories):
            time.sleep(sleep_s)

    summary = {
        "total": len(categories),
        "ok": ok,
        "skipped": skipped,
        "failed": failed,
        "errors": errors,
    }
    logger.info(
        "Category monthly download done: ok=%s skipped=%s failed=%s",
        ok,
        skipped,
        failed,
    )
    return summary


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Download Morningstar category average monthly data into the database. "
            f"Pass --token or set {TOKEN_ENV}."
        )
    )
    parser.add_argument(
        "--token",
        default=None,
        help=(
            f"SAL access_token (default: env {TOKEN_ENV}, else file at "
            f"{TOKEN_PATH_ENV})"
        ),
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional max number of categories to download (for testing)",
    )
    parser.add_argument(
        "--asset-class",
        default=None,
        help="Optional filter, e.g. equity / bond / mixed",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.15,
        help="Pause between category requests in seconds (default: 0.15)",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default=None,
        help="Logging level (default: PORTFOLIO_LOG_LEVEL or INFO)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    configure_logging(args.log_level)
    token = resolve_access_token(args.token)
    if not token:
        logger.error(
            "Missing access token. Pass --token, set %s, or set %s to a token file.",
            TOKEN_ENV,
            TOKEN_PATH_ENV,
        )
        return 2
    try:
        download_category_monthly_data(
            token,
            limit=args.limit,
            asset_class=args.asset_class,
            sleep_s=args.sleep,
        )
    except DownloadError:
        return 1
    except ValueError as exc:
        logger.error("%s", exc)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
