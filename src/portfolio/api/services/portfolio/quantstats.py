import logging
import tempfile
from pathlib import Path

import pandas as pd
import quantstats as qs
from quantstats._plotting import core as qs_plot_core
from quantstats._plotting import wrappers as qs_plot_wrappers

logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)

# Match management-tab chart colors.
# QuantStats uses palette index 0 for benchmark and index 1 for strategy.
STRATEGY_COLOR = "#348dc1"
BENCHMARK_COLOR = "#c9a227"


def _apply_report_colors() -> None:
    """Override QuantStats FlatUI palette so report charts match the UI legend."""
    for module in (qs_plot_core, qs_plot_wrappers):
        colors = list(module._FLATUI_COLORS)
        colors[0] = BENCHMARK_COLOR
        colors[1] = STRATEGY_COLOR
        module._FLATUI_COLORS = colors


_apply_report_colors()


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
    _apply_report_colors()

    print(f"[*] Generating QuantStats report against benchmark: {benchmark.name}...")
    qs.reports.html(returns, benchmark, output=output_file)
    print(f"[+] Performance report successfully saved to: {output_file}")


def generate_performance_report_html(
    returns: pd.Series,
    benchmark: pd.Series,
) -> str:
    """Generate a QuantStats HTML report and return it as a string."""
    qs.extend_pandas()
    _apply_report_colors()

    with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tmp:
        output_path = tmp.name

    try:
        qs.reports.html(returns, benchmark, output=output_path)
        return Path(output_path).read_text(encoding="utf-8")
    finally:
        Path(output_path).unlink(missing_ok=True)
