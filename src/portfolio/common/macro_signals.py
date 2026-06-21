from collections.abc import Callable

import pandas as pd

MacroSignalFn = Callable[[pd.DataFrame], pd.DataFrame]

# Input series column names
UNEMPLOYMENT_RATE = "Unemployment_Rate"
HIGH_YIELD_SPREAD = "High_Yield_Spread"
FINANCIAL_STRESS_INDEX = "Financial_Stress_Index"
YIELD_SPREAD_10Y3M = "Yield_Spread_10Y3M"

# Derived macro columns
SAHM_MA3 = "Sahm_MA3"
SAHM_MIN_12M = "Sahm_Min_12M"
SAHM_VALUE = "Sahm_Value"

# Alert columns
ALERT_INVERTED_CURVE = "Alert_Inverted_Curve"
ALERT_SAHM = "Alert_Sahm"
ALERT_FINANCIAL_STRESS = "Alert_Financial_Stress"

# Aggregate macro columns
MACRO_CRISIS_VOTES = "Macro_Crisis_Votes"
MACRO_SYSTEM_LOCKED = "MACRO_SYSTEM_LOCKED"

MACRO_VOTE_ALERTS = [ALERT_INVERTED_CURVE, ALERT_FINANCIAL_STRESS]


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


MACRO_VOTE_ALERTS = [ALERT_INVERTED_CURVE, ALERT_FINANCIAL_STRESS]


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
