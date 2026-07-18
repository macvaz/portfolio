"""Pure market-signal calculations from a loaded market DataFrame."""

import pandas as pd

from portfolio.common.macro_constants import SP500_DEATH_CROSS


def calculate_market_signals(df: pd.DataFrame) -> pd.DataFrame:
    if "SP500" not in df.columns:
        return df
    sma50 = df["SP500"].rolling(window=50, min_periods=1).mean()
    sma200 = df["SP500"].rolling(window=200, min_periods=1).mean()
    df[SP500_DEATH_CROSS] = sma50 / sma200
    return df
