from portfolio import (
    process_macro_data,
    print_signals,
    download_portfolio_navs,
    calculate_buy_and_hold_returns,
    generate_performance_report,
)

import os
from datetime import date
from dotenv import load_dotenv

load_dotenv()

FRED_API_KEY = os.getenv("FRED_API_KEY")


def run(
    fred_series: list[tuple[str, str]],
    portfolio: dict[str, float],
    start_date: str,
    end_date: str,
):
    print("1. Computing macro signals from FRED...")
    df_macro = process_macro_data(FRED_API_KEY, fred_series, start_date, end_date)
    print_signals(df_macro, end_date)

    print("\n2. Computing portfolio returns from MorningStar...")
    navs_df = download_portfolio_navs(portfolio, start_date, end_date)
    portfolio_returns_df = calculate_buy_and_hold_returns(navs_df, portfolio)
    print("\n3. Calculating portfolio metrics...")
    generate_performance_report(
        portfolio_returns_df, "SPY", "portfolio_performance.html"
    )


if __name__ == "__main__":
    fred_series = [
        ("UNRATE", "Unemployment_Rate"),
        ("BAMLH0A0HYM2EY", "High_Yield_Spread"),
        ("STLFSI4", "Financial_Stress_Index"),
        ("T10Y3M", "Yield_Spread_10Y3M"),
    ]

    portfolio = {"ES0182527038": 0.20, "IE00BYX5NX33": 0.65, "IE00BYX5M476": 0.15}

    run(fred_series, portfolio, "2025-01-02", date.today().isoformat())
