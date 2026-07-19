import argparse
import os
from datetime import date

from dotenv import load_dotenv

from portfolio.common.macro_constants import (
    BREAKEVEN_INFLATION,
    FINANCIAL_STRESS_INDEX,
    HIGH_YIELD_SPREAD,
    REAL_INTEREST_RATES,
    UNEMPLOYMENT_RATE,
    YIELD_SPREAD_10Y3M,
)
from portfolio.batch.download import download

FRED_SERIES = [
    ("UNRATE", UNEMPLOYMENT_RATE),
    ("BAMLH0A0HYM2EY", HIGH_YIELD_SPREAD),
    ("STLFSI4", FINANCIAL_STRESS_INDEX),
    ("T10Y3M", YIELD_SPREAD_10Y3M),
    ("DFII10", REAL_INTEREST_RATES),
    ("T10YIE", BREAKEVEN_INFLATION),
]

load_dotenv()

FRED_API_KEY = os.getenv("FRED_API_KEY")


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
