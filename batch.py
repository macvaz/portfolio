import argparse
import os
from datetime import date
from pathlib import Path

# Non-root containers often have no writable HOME; avoid Matplotlib writing to /.config.
Path(os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")).mkdir(
    parents=True, exist_ok=True
)

from dotenv import load_dotenv

from portfolio.batch.download import download
from portfolio.common.health_check_descriptions import fred_series_from_fixture
from portfolio.logging_config import configure_logging

load_dotenv()

FRED_API_KEY = os.getenv("FRED_API_KEY")
FRED_SERIES = fred_series_from_fixture()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download portfolio data and macro health.")
    parser.add_argument(
        "--start-date",
        type=str,
        default="1995-01-01",
        help="Start date for downloads (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--end-date",
        type=str,
        default=date.today().isoformat(),
        help="End date for downloads (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default=None,
        help="Logging level (default: PORTFOLIO_LOG_LEVEL or INFO).",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    configure_logging(args.log_level)
    download(
        FRED_API_KEY,
        FRED_SERIES,
        args.start_date,
        args.end_date,
    )
