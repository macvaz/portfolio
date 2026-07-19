import argparse
import os
from datetime import date

from dotenv import load_dotenv

from portfolio.common.alert_descriptions import fred_series_from_fixture
from portfolio.batch.download import download

load_dotenv()

FRED_API_KEY = os.getenv("FRED_API_KEY")
FRED_SERIES = fred_series_from_fixture()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download portfolio data and signals.")
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
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    download(
        FRED_API_KEY,
        FRED_SERIES,
        args.start_date,
        args.end_date,
    )
