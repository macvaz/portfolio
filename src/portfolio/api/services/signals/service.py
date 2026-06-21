"""Tactical signals service."""

from datetime import date
from functools import reduce
import pandas as pd

df = pd.DataFrame()


def get_signals() -> dict:
    """Return tactical signals. Mock implementation for now."""
    return {
        "as_of": date.today().isoformat(),
        "macro": [],
        "market": [],
    }


def momentum(df, window=14):
    return df.assign(
        momentum=lambda df: df["close"].diff(window),
        momentum_pct=lambda df: df["close"].pct_change(window),
    )


def volatility(df, window=14):
    return df.assign(volatility=lambda df: df["close"].rolling(window).std())


def rsi(df, window=14):
    delta = df["close"].diff()
    gain = delta.clip(lower=0).rolling(window).mean()
    loss = -delta.clip(upper=0).rolling(window).mean()
    return df.assign(rsi=lambda df: 100 - (100 / (1 + gain / loss)))


def compute_dynamic_signals(df: pd.DataFrame) -> pd.DataFrame:
    signals = [momentum, volatility, rsi]
    return reduce(lambda df, sig: df.pipe(sig), signals, df)
