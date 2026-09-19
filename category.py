import argparse
import os
import sys
from pathlib import Path

# Non-root containers often have no writable HOME; avoid Matplotlib writing to /.config.
Path(os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")).mkdir(
    parents=True, exist_ok=True
)

from dotenv import load_dotenv

from portfolio.batch.categories import (
    TOKEN_PATH_ENV,
    download_category_monthly_data,
)
from portfolio.datasource.errors import DownloadError
from portfolio.logging_config import configure_logging

load_dotenv()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download Morningstar category monthly average data."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional max number of categories to download (for testing).",
    )
    parser.add_argument(
        "--asset-class",
        default=None,
        help="Optional filter, e.g. equity / bond / mixed.",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.15,
        help="Pause between category requests in seconds (default: 0.15).",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default=None,
        help="Logging level (default: PORTFOLIO_LOG_LEVEL or INFO).",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    configure_logging(args.log_level)

    token_path = os.environ.get(TOKEN_PATH_ENV, "").strip()
    if not token_path:
        print(
            f"Error: {TOKEN_PATH_ENV} is not defined "
            "(path to the Morningstar bearer token file).",
            file=sys.stderr,
        )
        return 2

    path = Path(token_path)
    if not path.is_file():
        print(
            f"Error: token file not found: {path} ({TOKEN_PATH_ENV}).",
            file=sys.stderr,
        )
        return 2

    token = path.read_text(encoding="utf-8").strip()
    if not token:
        print(
            f"Error: token file is empty: {path} ({TOKEN_PATH_ENV}).",
            file=sys.stderr,
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
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
