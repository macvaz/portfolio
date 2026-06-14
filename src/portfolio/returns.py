import numpy as np
import pandas as pd


def calculate_buy_and_hold_returns(
    returns_df: pd.DataFrame, initial_weights: list
) -> pd.DataFrame:
    """Calculates the evolution of a portfolio based on an initial 1-unit investment

    using a Buy and Hold strategy (no rebalancing).

    Parameters:
    returns_df (pd.DataFrame): DataFrame where columns are assets and rows are
    time periods
                               containing assets' returns (e.g., 0.05 for 5%).
    initial_weights (list): List or array of initial weights for each asset.
                            Must sum up to 1.0.

    Returns:
    pd.DataFrame: A DataFrame containing the individual asset evolutions,
                  and the final total portfolio value indexed to base 1.
    """
    # Convert weights to a numpy array for vector operations
    weights = np.array(initial_weights)

    # Step 1: Calculate the cumulative return (Base 1) for each individual asset
    # (1 + R).cumprod()
    individual_assets_base_1 = (1 + returns_df).cumprod()

    # Step 2: Multiply each asset's evolution by its initial weight
    weighted_assets = individual_assets_base_1 * weights

    # Step 3: Sum across rows to get the total portfolio value over time
    portfolio_evolution = pd.DataFrame(index=returns_df.index)
    portfolio_evolution["portfolio_base_1"] = weighted_assets.sum(axis=1)

    # Optional: If you want to see the performance of each asset inside the portfolio
    # you can uncomment the following line:
    # portfolio_evolution = pd.concat([weighted_assets, portfolio_evolution], axis=1)

    return portfolio_evolution