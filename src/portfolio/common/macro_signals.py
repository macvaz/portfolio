from collections.abc import Callable

import pandas as pd

from portfolio.common.macro_constants import (
    FINANCIAL_STRESS,
    FINANCIAL_STRESS_INDEX,
    INVERTED_CURVE,
    YIELD_SPREAD_10Y3M,
)

MacroSignalFn = Callable[[pd.DataFrame], pd.DataFrame]


def inverted_curve(df: pd.DataFrame) -> pd.DataFrame:
    return df.assign(**{INVERTED_CURVE: lambda d: d[YIELD_SPREAD_10Y3M] < 0})


def financial_stress(df: pd.DataFrame) -> pd.DataFrame:
    return df.assign(
        **{FINANCIAL_STRESS: lambda d: d[FINANCIAL_STRESS_INDEX] >= 1.0}
    )
