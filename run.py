import dataclasses
from portfolio import process_macro_data, print_signals
from portfolio.funds import search_by_isin
from portfolio.download import download_price_data

import os
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

FRED_API_KEY = os.getenv("FRED_API_KEY")

FRED_SERIES = [
    ("UNRATE", "Unemployment_Rate"),
    ("BAMLH0A0HYM2EY", "High_Yield_Spread"),
    ("STLFSI4", "Financial_Stress_Index"),
    ("T10Y3M", "Yield_Spread_10Y3M"),
]

PORTFOLIO_ISINS = [
    "ES0182527038"
]

START_DATE = "2025-01-01"
END_DATE = "2026-06-11"

if __name__ == "__main__":
    df_macro = process_macro_data(FRED_API_KEY, FRED_SERIES, start_date=START_DATE, end_date=END_DATE)
    print_signals(df_macro, END_DATE)

    print("\nWorking with the portfolio...")
    for isin in PORTFOLIO_ISINS:
        fund = search_by_isin(isin)
        if fund is None:
            print(f"No fund found for ISIN: {isin}")
            continue
        fund_data = download_price_data(fund['security_id'], "EUR", START_DATE, END_DATE)
        print(fund_data)