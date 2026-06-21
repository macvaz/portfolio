from datetime import date
import os

from dotenv import load_dotenv

from portfolio.api.database import DEFAULT_DB_PATH
from portfolio.common.navs import DEFAULT_FUNDS_DIR
from portfolio.job.download import download

load_dotenv()

FRED_API_KEY = os.getenv("FRED_API_KEY")

FRED_SERIES = [
    ("UNRATE", "Unemployment_Rate"),
    ("BAMLH0A0HYM2EY", "High_Yield_Spread"),
    ("STLFSI4", "Financial_Stress_Index"),
    ("T10Y3M", "Yield_Spread_10Y3M"),
]

if __name__ == "__main__":
    download(
        FRED_API_KEY,
        FRED_SERIES,
        "2000-01-01",
        date.today().isoformat(),
        "EUR",
        DEFAULT_DB_PATH,
        DEFAULT_FUNDS_DIR,
    )
