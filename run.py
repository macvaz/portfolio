from portfolio import process_macro_data, print_signals
from portfolio.funds import resolve_fund_by_isin
from portfolio.download import download_price_data
from portfolio.returns import calculate_buy_and_hold_returns

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

PORTFOLIO_ISINS = {
    "ES0182527038": 0.20,
    "IE00BYX5NX33": 0.65,
    "IE00BYX5M476": 0.15
}

START_DATE = "2025-01-01"
END_DATE = "2026-06-11"

if __name__ == "__main__":
    df_macro = process_macro_data(FRED_API_KEY, FRED_SERIES, start_date=START_DATE, end_date=END_DATE)
    print_signals(df_macro, END_DATE)

    print("\nWorking with the portfolio...")
    price_series = {}
    for isin, weight in PORTFOLIO_ISINS.items():
        fund = resolve_fund_by_isin(isin)
        if fund is None:
            print(f"No fund found for ISIN: {isin}")
            continue
        fund_data = download_price_data(fund["security_id"], "EUR", START_DATE, END_DATE)
        if fund_data.empty:
            print(f"No price data for ISIN: {isin}")
            continue
        price_series[isin] = fund_data["value"]
        print(f"{isin} ({weight:.0%}): {fund['name']}")

    if price_series:
        prices_df = pd.DataFrame(price_series).dropna()
        returns_df = prices_df.pct_change().dropna()
        weights = [PORTFOLIO_ISINS[isin] for isin in returns_df.columns]
        portfolio = calculate_buy_and_hold_returns(returns_df, weights)
        print("\nPortfolio evolution (base 1):")
        print(portfolio)