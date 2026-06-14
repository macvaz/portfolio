import logging
import tempfile
from pathlib import Path

import pandas as pd
import quantstats as qs

logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)


def generate_performance_report(
    df: pd.DataFrame, benchmark: str = "SPY", output_file: str = "report.html"
):
    """
    Generates a comprehensive QuantStats HTML report for a given series of prices or returns.

    Args:
        df: DataFrame containing price data (expects the first column to be the primary series).
        benchmark: Ticker symbol for the benchmark (e.g., 'SPY', '^GSPC').
        output_file: Path where the HTML report will be saved.
    """
    # Extend pandas with quantstats methods
    qs.extend_pandas()

    # Calculate returns from the first column of the DataFrame
    # QuantStats works best with a Series of daily returns
    returns = df.iloc[:, 0].pct_change().dropna()

    print(f"[*] Generating QuantStats report against benchmark: {benchmark}...")
    qs.reports.html(returns, benchmark, output=output_file)
    print(f"[+] Performance report successfully saved to: {output_file}")


def generate_performance_report_html(
    df: pd.DataFrame, benchmark: str = "SPY"
) -> str:
    """Generate a QuantStats HTML report and return it as a string."""
    qs.extend_pandas()
    returns = df.iloc[:, 0].pct_change().dropna()

    with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tmp:
        output_path = tmp.name

    try:
        qs.reports.html(returns, benchmark, output=output_path)
        return Path(output_path).read_text(encoding="utf-8")
    finally:
        Path(output_path).unlink(missing_ok=True)
