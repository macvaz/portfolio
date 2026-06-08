from portfolio.series import download_series
from portfolio.signals import calculate_signals, print_signals
import pandas as pd

FRED_API_KEY = "30b30cb68b46901be58d1865913c964b" 

FRED_SERIES = [
    ("UNRATE", "Unemployment_Rate"),
    ("BAMLH0A0HYM2EY", "High_Yield_Spread"),
    ("STLFSI4", "Financial_Stress_Index"),
    ("T10Y3M", "Yield_Spread_10Y3M"),
]

pd.set_option('display.max_columns', None)
pd.set_option('display.max_colwidth', None)

if __name__ == "__main__":
    df_series = download_series(FRED_API_KEY, FRED_SERIES, start_date="2020-01-01", end_date="2020-04-30")
    df_final = calculate_signals(df_series)

    print_signals(df_final, "2020-04-01")