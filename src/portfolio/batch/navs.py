"""Batch-download fund NAVs for every fund stored in the database."""

from pathlib import Path

from portfolio.storage.database import list_funds
from portfolio.common.navs import download_and_store_fund_nav
from portfolio.datasource.errors import DownloadError


def store_fund_navs_from_db(
    start_date: str,
    end_date: str,
    *,
    currency: str = "EUR",
    db_path: Path | None = None,
    funds_dir: Path | None = None,
) -> list[Path]:
    """Download NAV series for all funds in the DB and store one CSV per ISIN."""
    funds = list_funds(db_path)
    if not funds:
        print(
            "No funds found in database. Add funds via the web UI "
            "(Morningstar JSON import) before running get-data."
        )
        return []

    saved_paths: list[Path] = []
    failures: list[str] = []
    for fund in funds:
        isin = fund["isin"]
        name = fund["name"]
        try:
            path = download_and_store_fund_nav(
                isin,
                fund["fund_id"],
                start_date=start_date,
                end_date=end_date,
                currency=currency,
                funds_dir=funds_dir,
            )
        except DownloadError as exc:
            failures.append(f"{isin} ({name}): {exc}")
            continue

        if path is None:
            failures.append(f"{isin} ({name}): no NAV data returned")
            continue

        print(f"[saved] {isin}: {name} -> {path}")
        saved_paths.append(path)

    print(f"Done. Saved {len(saved_paths)} of {len(funds)} fund file(s).")
    if failures:
        raise DownloadError(
            f"Fund NAV download failed for {len(failures)} fund(s):\n- "
            + "\n- ".join(failures)
        )
    return saved_paths
