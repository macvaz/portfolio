from pathlib import Path

from portfolio.storage.database import DEFAULT_DB_PATH
from portfolio.common.navs import DEFAULT_FUNDS_DIR
from portfolio.common.series import DEFAULT_SERIES_DIR
from portfolio.batch.alert_storage import persist_latest_alerts
from portfolio.batch.metrics import update_all_fund_metrics
from portfolio.batch.navs import store_fund_navs_from_db
from portfolio.batch.signals import compute_signals


def download(
    fred_api_key: str | None,
    fred_series: list[tuple[str, str]],
    start_date: str,
    end_date: str,
    currency: str = "EUR",
    db_path: Path = DEFAULT_DB_PATH,
    funds_dir: Path = DEFAULT_FUNDS_DIR,
    series_dir: Path = DEFAULT_SERIES_DIR,
):
    print("Downloading FRED series...")
    market_df = compute_signals(
        fred_api_key,
        fred_series,
        start_date,
        end_date,
        series_dir=series_dir,
    )
    observation_date = persist_latest_alerts(
        market_df,
        series_dir=series_dir,
        db_path=db_path,
    )
    if observation_date is not None:
        print(f"Stored tactical alerts for {observation_date.isoformat()}.")

    print("\nDownloading fund NAVs from Morningstar...")
    store_fund_navs_from_db(
        start_date,
        end_date,
        currency=currency,
        db_path=db_path,
        funds_dir=funds_dir,
    )

    print("\nComputing fund metrics...")
    updated = update_all_fund_metrics(db_path, funds_dir)
    print(f"Done. Updated metrics for {updated} fund(s).")
