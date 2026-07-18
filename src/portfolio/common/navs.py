from pathlib import Path

import pandas as pd

from portfolio.datasources.morningstar import download_navs

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
    """Download one fund NAV series from Morningstar and write it to CSV."""
    nav_df = download_navs(
        fund_id=fund_id,
        start=start_date,
        end=end_date,
        currency=currency,
    )
    if nav_df.empty:
        return None
    return save_fund_nav_csv(isin, nav_df, funds_dir)
