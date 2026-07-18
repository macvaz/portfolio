from portfolio.api.services.portfolio.quantstats import (
    generate_performance_report,
    generate_performance_report_html,
)
from portfolio.common.equity import calculate_buy_and_hold_returns
from portfolio.datasources.morningstar import download_navs


def test_package_exports():
    assert callable(download_navs)
    assert callable(calculate_buy_and_hold_returns)
    assert callable(generate_performance_report)
    assert callable(generate_performance_report_html)
