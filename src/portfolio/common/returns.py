import numpy as np
import pandas as pd


def calculate_buy_and_hold_returns(
    navs_df: pd.DataFrame,
    portfolio: dict[str, float],
    cash_weight: float = 0.0,
) -> pd.DataFrame:
    """Calculate buy-and-hold portfolio evolution from asset NAVs.

    Converts price series to returns, applies initial weights without rebalancing,
    and returns the total portfolio value indexed to base 1.

    Parameters:
    navs_df (pd.DataFrame): Asset NAVs or prices indexed by date. Columns are
                            asset identifiers (e.g. ISINs).
    portfolio (dict[str, float]): Mapping of asset identifier to initial weight.
                                  Weights must match navs_df columns and sum to
                                  at most 1.0 when combined with ``cash_weight``.
    cash_weight (float): Uninvested cash weight (0 return), so weights + cash = 1.0.

    Returns:
    pd.DataFrame: Single-column DataFrame with ``portfolio_base_1`` indexed to 1.0
                  at the start of the period.
    """

    navs_df = navs_df.dropna()
    returns_df = navs_df.pct_change().dropna()
    weights = [portfolio[isin] for isin in returns_df.columns]
    weights = np.array(weights)

    # Step 1: Calculate the cumulative return (Base 1) for each individual asset
    # (1 + R).cumprod()
    individual_assets_base_1 = (1 + returns_df).cumprod()

    # Step 2: Multiply each asset's evolution by its initial weight
    weighted_assets = individual_assets_base_1 * weights

    # Step 3: Sum across rows to get the total portfolio value over time
    portfolio_evolution = pd.DataFrame(index=returns_df.index)
    portfolio_evolution["portfolio_base_1"] = weighted_assets.sum(axis=1) + cash_weight

    return portfolio_evolution
