import logging
from pathlib import Path

from portfolio.api.services.risk.risk_report import warm_all_risk_report_caches
from portfolio.batch.alert_storage import persist_latest_alerts
from portfolio.batch.metrics import update_all_fund_metrics
from portfolio.batch.navs import store_fund_navs_from_db
from portfolio.batch.signals import compute_signals
from portfolio.common.indexes import DEFAULT_INDEXES_DIR
from portfolio.common.navs import DEFAULT_FUNDS_DIR
from portfolio.common.series import DEFAULT_SERIES_DIR
from portfolio.datasource.errors import DownloadError
from portfolio.storage.database import DEFAULT_DB_PATH

logger = logging.getLogger(__name__)


def download(
    fred_api_key: str | None,
    fred_series: list[tuple[str, str]],
    start_date: str,
    end_date: str,
    currency: str = "EUR",
    db_path: Path = DEFAULT_DB_PATH,
    funds_dir: Path = DEFAULT_FUNDS_DIR,
    series_dir: Path = DEFAULT_SERIES_DIR,
    indexes_dir: Path = DEFAULT_INDEXES_DIR,
):
    logger.info("Downloading macro series from FRED...")
    try:
        market_df = compute_signals(
            fred_api_key,
            fred_series,
            start_date,
            end_date,
            series_dir=series_dir,
            indexes_dir=indexes_dir,
        )
    except DownloadError as exc:
        logger.error("Market signal download failed: %s", exc)
        raise

    observation_date = persist_latest_alerts(
        market_df,
        indexes_dir=indexes_dir,
        db_path=db_path,
    )
    if observation_date is not None:
        logger.info("Stored macro health data for %s.", observation_date.isoformat())

    logger.info("Downloading fund NAVs from Morningstar...")
    store_fund_navs_from_db(
        start_date,
        end_date,
        currency=currency,
        db_path=db_path,
        funds_dir=funds_dir,
    )

    logger.info("Computing fund metrics...")
    updated = update_all_fund_metrics(db_path, funds_dir)
    logger.info("Done. Updated metrics for %s fund(s).", updated)

    logger.info("Warming portfolio risk report caches...")
    warmed = warm_all_risk_report_caches(db_path=db_path, funds_dir=funds_dir)
    logger.info("Warmed risk report cache for %s portfolio(s).", warmed)
