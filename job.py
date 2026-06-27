import os
from datetime import date

from dotenv import load_dotenv

from portfolio.common.macro_constants import (
    FINANCIAL_STRESS_INDEX,
    HIGH_YIELD_SPREAD,
    SAHM_RULE_INDICATOR,
    UNEMPLOYMENT_RATE,
    YIELD_SPREAD_10Y3M,
)
from portfolio.common.macro_signals import financial_stress, inverted_curve
from portfolio.job.download import download

FRED_SERIES = [
    ("UNRATE", UNEMPLOYMENT_RATE),
    ("BAMLH0A0HYM2EY", HIGH_YIELD_SPREAD),
    ("STLFSI4", FINANCIAL_STRESS_INDEX),
    ("T10Y3M", YIELD_SPREAD_10Y3M),
    ("SAHMREALTIME", SAHM_RULE_INDICATOR),
]

MACRO_SIGNALS = [
    inverted_curve,
    financial_stress,
]


load_dotenv()

FRED_API_KEY = os.getenv("FRED_API_KEY")

if __name__ == "__main__":
    download(
        FRED_API_KEY,
        FRED_SERIES,
        MACRO_SIGNALS,
        "2000-01-01",
        date.today().isoformat(),
    )
