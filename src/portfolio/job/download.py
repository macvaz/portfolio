from pathlib import Path

from portfolio.api.database import DEFAULT_DB_PATH
from portfolio.common.macro_signals import MacroSignalFn
from portfolio.common.metrics import update_all_fund_metrics
from portfolio.common.navs import DEFAULT_FUNDS_DIR, store_fund_navs_from_db
from portfolio.common.signals import compute_signals
from portfolio.datasources.morningstar import import_isins


def download(
    fred_api_key: str | None,
    fred_series: list[tuple[str, str]],
    macro_signals: list[MacroSignalFn],
    start_date: str,
    end_date: str,
    currency: str = "EUR",
    db_path: Path = DEFAULT_DB_PATH,
    funds_dir: Path = DEFAULT_FUNDS_DIR,
):
    print("Downloading FRED series...")
    compute_signals(fred_api_key, fred_series, macro_signals, start_date, end_date)

    print("\nDownloading fund NAVs from Morningstar...")
    store_fund_navs_from_db(
        start_date,
        end_date,
        currency=currency,
        db_path=db_path,
        funds_dir=funds_dir,
    )

    print("\nBackfilling Morningstar fund links...")
    linked = import_isins(db_path=db_path)
    print(f"Done. Linked {linked} fund(s).")

    print("\nComputing fund metrics...")
    updated = update_all_fund_metrics(db_path, funds_dir)
    print(f"Done. Updated metrics for {updated} fund(s).")
