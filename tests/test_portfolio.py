from portfolio import (
    calculate_buy_and_hold_returns,
    download_portfolio_navs,
    generate_performance_report,
    generate_performance_report_html,
    process_macro_data,
)


def test_package_exports():
    assert callable(process_macro_data)
    assert callable(download_portfolio_navs)
    assert callable(calculate_buy_and_hold_returns)
    assert callable(generate_performance_report)
    assert callable(generate_performance_report_html)
