from portfolio import process_macro_data, print_signals
from portfolio.download import download_portfolio_navs
from portfolio.returns import calculate_buy_and_hold_returns
from portfolio.analysis import generate_performance_report

import os
from dotenv import load_dotenv

load_dotenv()

FRED_API_KEY = os.getenv("FRED_API_KEY")

FRED_SERIES = [
    ("UNRATE", "Unemployment_Rate"),
    ("BAMLH0A0HYM2EY", "High_Yield_Spread"),
    ("STLFSI4", "Financial_Stress_Index"),
    ("T10Y3M", "Yield_Spread_10Y3M"),
]

PORTFOLIO = {
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
    navs_df = download_portfolio_navs(PORTFOLIO, START_DATE, END_DATE)

    portfolio_df = calculate_buy_and_hold_returns(navs_df, PORTFOLIO)
    print(portfolio_df)
    generate_performance_report(portfolio_df, "SPY", "portfolio_performance.html")