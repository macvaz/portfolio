import argparse
import os
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

from portfolio.common.macro_constants import (
    FINANCIAL_STRESS_INDEX,
    HIGH_YIELD_SPREAD,
    REAL_INTEREST_RATES,
    SAHM_RULE_INDICATOR,
    UNEMPLOYMENT_RATE,
    YIELD_SPREAD_10Y3M,
)
from portfolio.datasources.sp500 import DEFAULT_BACKTEST_SP500_PATH
from portfolio.job.download import download

FRED_SERIES = [
    ("UNRATE", UNEMPLOYMENT_RATE),
    ("BAMLH0A0HYM2EY", HIGH_YIELD_SPREAD),
    ("STLFSI4", FINANCIAL_STRESS_INDEX),
    ("T10Y3M", YIELD_SPREAD_10Y3M),
    ("DFII10", REAL_INTEREST_RATES),
    ("SAHMREALTIME", SAHM_RULE_INDICATOR),
]

load_dotenv()

FRED_API_KEY = os.getenv("FRED_API_KEY")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download portfolio data and signals.")
    parser.add_argument(
        "--backtest",
        action="store_true",
        help=(
            "Use data/backtest/sp500.csv for SP500 and death-cross signals "
            "instead of downloading SP500 from Yahoo Finance."
        ),
    )
    parser.add_argument(
        "--backtest-sp500-path",
        type=str,
        default=str(DEFAULT_BACKTEST_SP500_PATH),
        help="Path to the backtest SP500 CSV (used with --backtest).",
    )
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
        backtest=args.backtest,
        backtest_sp500_path=Path(args.backtest_sp500_path),
    )
