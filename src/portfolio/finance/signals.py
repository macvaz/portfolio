import pandas as pd


def calculate_macro_signals(df: pd.DataFrame) -> pd.DataFrame:
    # --- INDICATOR 1: THE FED'S SPREAD (10Y - 3M) ---
    # Trigger signal if the yield curve inverts (drops below 0)
    df["Alert_Inverted_Curve"] = df["Yield_Spread_10Y3M"] < 0

    # --- INDICATOR 2: THE SAHM RULE (Unemployment Filter) ---
    # 3-month moving average of the unemployment rate (~63 trading days)
    df["Sahm_MA3"] = df["Unemployment_Rate"].rolling(window=63).mean()
    # 12-month minimum of the unemployment rate (~252 trading days)
    df["Sahm_Min_12M"] = df["Unemployment_Rate"].rolling(window=252).min()
    # Sahm Indicator value
    df["Sahm_Value"] = df["Sahm_MA3"] - df["Sahm_Min_12M"]
    df["Alert_Sahm"] = df["Sahm_Value"] 
    # --- INDICATOR 4: ST. LOUIS FINANCIAL STRESS INDEX (Liquidity Filter) ---
    # Trigger signal if the index exceeds 1.0 (High financial stress)
    df["Alert_Financial_Stress"] = df["Financial_Stress_Index"] >= 1.0

    # --- MACRO VOTING MATRIX ---
    # Count how many alerts are triggered concurrently
    df["Macro_Crisis_Votes"] = (
        df["Alert_Inverted_Curve"].astype(int)
        + df["Alert_Sahm"].astype(int)
        + df["Alert_High_Yield"].astype(int)
        + df["Alert_Financial_Stress"].astype(int)
    )

    # Risk-off Confirmation: Recommends activating defensive bunker if there are 2 or more votes
    df["MACRO_SYSTEM_LOCKED"] = df["Macro_Crisis_Votes"] >= 2

    return df


def calculate_market_signals(df: pd.DataFrame) -> pd.DataFrame:
    df["SP500_SMA50"] = df["SP500"].rolling(window=50, min_periods=1).mean()
    df["SP500_SMA200"] = df["SP500"].rolling(window=200, min_periods=1).mean()

    # Death cross event: SMA50 crosses below SMA200 (from yesterday to today)
    df["SP500_Death_Cross"] = (
        df["SP500_SMA50"].shift(1) >= df["SP500_SMA200"].shift(1)
    ) & (df["SP500_SMA50"] < df["SP500_SMA200"])
    # Active state while SMA50 remains below SMA200
    df["SP500_Death_Cross_Active"] = df["SP500_SMA50"] < df["SP500_SMA200"]

    # Confirmed death cross: SMA50 is 5% or more below SMA200
    df["SP500_Confirmed_Death_Cross"] = df["SP500_SMA50"] <= (df["SP500_SMA200"] * 0.95)

    return df


def print_signals(df: pd.DataFrame, date: str):
    if date in df.index:
        row = df.loc[date]

        print("\nMacro signals")
        print(
            f"1. Curve Inversion (10Y-3M): {float(row['Yield_Spread_10Y3M']):.2f}% -> {row['Alert_Inverted_Curve']}"
        )
        print(
            f"2. Sahm Rule (Employment): {float(row['Sahm_Value']):.2f}% -> {row['Alert_Sahm']}"
        )
        print(
            f"3. High Yield Spread (Credit): {float(row['High_Yield_Spread']):.2f}% -> {row['Alert_High_Yield']}"
        )
        print(
            f"4. Financial Stress Index: {float(row['Financial_Stress_Index']):.2f} -> {row['Alert_Financial_Stress']}"
        )

        print("\nMarket signals")
        print(f"5. SP500 Death Cross: {row['SP500_Death_Cross_Active']}")
        print(f"6. SP500 Confirmed Death Cross: {row['SP500_Confirmed_Death_Cross']}")
