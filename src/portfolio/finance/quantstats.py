import logging
import tempfile
from pathlib import Path

import pandas as pd
import quantstats as qs

logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)


def generate_performance_report(
    returns: pd.Series,
    benchmark: pd.Series,
    output_file: str = "report.html",
):
    """
    Generates a comprehensive QuantStats HTML report for daily return series.

    Args:
        returns: Daily simple returns for the portfolio/strategy.
        benchmark: Daily simple returns for the benchmark.
        output_file: Path where the HTML report will be saved.
    """
    qs.extend_pandas()

    print(f"[*] Generating QuantStats report against benchmark: {benchmark.name}...")
    qs.reports.html(returns, benchmark, output=output_file)
    print(f"[+] Performance report successfully saved to: {output_file}")


def generate_performance_report_html(
    returns: pd.Series,
    benchmark: pd.Series,
) -> str:
    """Generate a QuantStats HTML report and return it as a string."""
    qs.extend_pandas()

    with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tmp:
        output_path = tmp.name

    try:
        qs.reports.html(returns, benchmark, output=output_path)
        return Path(output_path).read_text(encoding="utf-8")
    finally:
        Path(output_path).unlink(missing_ok=True)
