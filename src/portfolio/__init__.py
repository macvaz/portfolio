from .series import download_series
from .signals import calculate_macro_signals, calculate_market_signals, print_signals

import pandas as pd

def process_macro_data(FRED_API_KEY, FRED_SERIES, start_date, end_date) -> pd.DataFrame:
    df_series = download_series(FRED_API_KEY, FRED_SERIES, start_date=start_date, end_date=end_date)
    df_macro = calculate_macro_signals(df_series)
    df_final = calculate_market_signals(df_macro)
    return df_final
    

__all__ = [
    "process_macro_data",
    "print_signals",
]