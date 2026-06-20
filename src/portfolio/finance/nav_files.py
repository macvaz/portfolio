from pathlib import Path

import pandas as pd

from portfolio.api.database import list_funds
from portfolio.finance.download import download_fund_navs

DEFAULT_FUNDS_DIR = Path("data/funds")


def fund_nav_path(isin: str, funds_dir: Path | None = None) -> Path:
    root = funds_dir or DEFAULT_FUNDS_DIR
    return root / f"{isin.upper()}.csv"


def nav_dataframe_to_csv(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize a downloaded NAV series to ``date`` and ``nav`` columns."""
    if df.empty:
        return pd.DataFrame(columns=["date", "nav"])

    out = df.copy()
    if "value" in out.columns:
        out = out.rename(columns={"value": "nav"})
    elif "nav" not in out.columns and len(out.columns) == 1:
        out = out.rename(columns={out.columns[0]: "nav"})

    if "date" not in out.columns:
        out = out.reset_index()
        date_col = out.columns[0]
        out = out.rename(columns={date_col: "date"})

    out["date"] = pd.to_datetime(out["date"]).dt.strftime("%Y-%m-%d")
    return out[["date", "nav"]].sort_values("date")


def save_fund_nav_csv(
    isin: str, nav_df: pd.DataFrame, funds_dir: Path | None = None
) -> Path:
    path = fund_nav_path(isin, funds_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    nav_dataframe_to_csv(nav_df).to_csv(path, index=False)
    return path


def load_fund_nav_csv(isin: str, funds_dir: Path | None = None) -> pd.DataFrame:
    path = fund_nav_path(isin, funds_dir)
    if not path.exists():
        return pd.DataFrame()

    df = pd.read_csv(path, parse_dates=["date"])
    return df.set_index("date").sort_index()


def delete_fund_nav_csv(isin: str, funds_dir: Path | None = None) -> bool:
    path = fund_nav_path(isin, funds_dir)
    if not path.exists():
        return False
    path.unlink()
    return True


def download_and_store_fund_nav(
    isin: str,
    fund_id: str,
    *,
    start_date: str,
    end_date: str,
    currency: str = "EUR",
    funds_dir: Path | None = None,
) -> Path | None:
    nav_df = download_fund_navs(fund_id, currency, start_date, end_date)
    if nav_df.empty:
        return None
    return save_fund_nav_csv(isin, nav_df, funds_dir)


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
            "No funds found in database. Add funds via the API "
            "(POST /api/funds) before running get-data."
        )
        return []

    saved_paths: list[Path] = []
    for fund in funds:
        isin = fund["isin"]
        name = fund["name"]
        path = download_and_store_fund_nav(
            isin,
            fund["fund_id"],
            start_date=start_date,
            end_date=end_date,
            currency=currency,
            funds_dir=funds_dir,
        )
        if path is None:
            print(f"[skip] {isin}: no NAV data for {name}")
            continue

        print(f"[saved] {isin}: {name} -> {path}")
        saved_paths.append(path)

    print(f"Done. Saved {len(saved_paths)} of {len(funds)} fund file(s).")
    return saved_paths
