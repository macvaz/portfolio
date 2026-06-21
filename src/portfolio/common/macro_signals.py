from collections.abc import Callable

import pandas as pd

from portfolio.common.macro_constants import (
    ALERT_FINANCIAL_STRESS,
    ALERT_INVERTED_CURVE,
    ALERT_SAHM,
    FINANCIAL_STRESS_INDEX,
    MACRO_CRISIS_VOTES,
    MACRO_SYSTEM_LOCKED,
    MACRO_VOTE_ALERTS,
    SAHM_MA3,
    SAHM_MIN_12M,
    SAHM_VALUE,
    UNEMPLOYMENT_RATE,
    YIELD_SPREAD_10Y3M,
)

MacroSignalFn = Callable[[pd.DataFrame], pd.DataFrame]


def inverted_curve(df: pd.DataFrame) -> pd.DataFrame:
    return df.assign(**{ALERT_INVERTED_CURVE: lambda d: d[YIELD_SPREAD_10Y3M] < 0})


def sahm_rule(df: pd.DataFrame) -> pd.DataFrame:
    return df.assign(
        **{
            SAHM_MA3: lambda d: d[UNEMPLOYMENT_RATE].rolling(window=63).mean(),
            SAHM_MIN_12M: lambda d: d[UNEMPLOYMENT_RATE].rolling(window=252).min(),
        }
    ).assign(
        **{
            SAHM_VALUE: lambda d: d[SAHM_MA3] - d[SAHM_MIN_12M],
            ALERT_SAHM: lambda d: d[SAHM_VALUE],
        }
    )


def financial_stress(df: pd.DataFrame) -> pd.DataFrame:
    return df.assign(
        **{ALERT_FINANCIAL_STRESS: lambda d: d[FINANCIAL_STRESS_INDEX] >= 1.0}
    )


def macro_crisis_votes(
    df: pd.DataFrame, vote_columns: list[str] = MACRO_VOTE_ALERTS
) -> pd.DataFrame:
    return df.assign(
        **{
            MACRO_CRISIS_VOTES: lambda d: sum(
                d[column].astype(int) for column in vote_columns
            ),
            MACRO_SYSTEM_LOCKED: lambda d: d[MACRO_CRISIS_VOTES] >= 2,
        }
    )


MACRO_SIGNALS: list[MacroSignalFn] = [
    inverted_curve,
    sahm_rule,
    financial_stress,
    macro_crisis_votes,
]
