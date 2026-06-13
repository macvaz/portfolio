from portfolio.series import download_series
from portfolio.signals import calculate_macro_signals, calculate_market_signals, print_signals
from portfolio.funds import add_new_funds

import pandas as pd

FRED_API_KEY = "30b30cb68b46901be58d1865913c964b" 

FRED_SERIES = [
    ("UNRATE", "Unemployment_Rate"),
    ("BAMLH0A0HYM2EY", "High_Yield_Spread"),
    ("STLFSI4", "Financial_Stress_Index"),
    ("T10Y3M", "Yield_Spread_10Y3M"),
]

START_DATE = "2019-01-01"
END_DATE = "2020-04-30"

pd.set_option('display.max_columns', None)
pd.set_option('display.max_colwidth', None)

if __name__ == "__main__":
    # df_series = download_series(FRED_API_KEY, FRED_SERIES, start_date=START_DATE, end_date=END_DATE)
    # df_macro = calculate_macro_signals(df_series)
    # df_final = calculate_market_signals(df_macro)

    # print_signals(df_final, END_DATE)

    # Adding new funds
    add_new_funds(["US0378331005", "US0231351067", "US5949181045"])