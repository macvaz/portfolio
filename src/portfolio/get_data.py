
from pathlib import Path

from portfolio import process_macro_data, print_signals
from portfolio.finance.metrics import update_all_fund_metrics
from portfolio.finance.funds import backfill_fund_performance_ids
from portfolio.finance.nav_files import store_fund_navs_from_db


def run(
    fred_api_key: str | None,
    fred_series: list[tuple[str, str]],
    start_date: str,
    end_date: str,
    currency: str = "EUR",
    db_path: Path | None = None,
    funds_dir: Path | None = None,
):
    if fred_api_key:
        print("1. Computing macro signals from FRED...")
        df_macro = process_macro_data(fred_api_key, fred_series, start_date, end_date)
        print_signals(df_macro, end_date)
    else:
        print("1. Skipping macro signals (FRED_API_KEY not set)")

    print("\n2. Downloading fund NAVs from Morningstar...")
    store_fund_navs_from_db(
        start_date,
        end_date,
        currency=currency,
        db_path=db_path,
        funds_dir=funds_dir,
    )

    print("\n3. Backfilling Morningstar fund links...")
    linked = backfill_fund_performance_ids(db_path)
    print(f"Done. Linked {linked} fund(s).")

    print("\n4. Computing fund metrics...")
    updated = update_all_fund_metrics(db_path, funds_dir)
    print(f"Done. Updated metrics for {updated} fund(s).")


