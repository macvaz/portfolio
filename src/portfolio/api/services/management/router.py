from datetime import date
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from portfolio.storage.database import (
    delete_fund,
    delete_user,
    get_db,
    list_funds,
    list_user_portfolio,
    list_users,
    save_fund,
    save_fund_metrics,
    save_user_portfolio,
    set_default_user,
)
from portfolio.storage.models import User
from portfolio.api.services.management.curve import build_user_equity_curve
from portfolio.api.services.management.metrics import get_portfolio_metrics
from portfolio.api.services.management.schemas import (
    FundResponse,
    PortfolioCreate,
    PortfolioListItem,
    PortfolioPositionResponse,
    PortfolioSave,
    normalize_portfolio_positions,
    require_portfolio,
)
from portfolio.api.services.risk.risk_report import warm_user_risk_report_cache
from portfolio.api.services.risk.risk_report_cache import (
    invalidate_all_risk_reports,
    invalidate_portfolio_risk_reports,
)
from portfolio.datasource.morningstar import (
    morningstar_quote_url,
    parse_morningstar_search,
)
from portfolio.datasource.errors import DownloadError
from portfolio.common.metrics import compute_fund_metrics
from portfolio.common.navs import delete_fund_nav_csv, download_and_store_fund_nav

router = APIRouter(prefix="/api/portfolio", tags=["management"])
NAV_START_DATE = "2000-01-01"
logger = logging.getLogger(__name__)


def _warm_risk_report_cache(portfolio_id: int) -> None:
    try:
        warm_user_risk_report_cache(portfolio_id)
    except Exception:
        logger.exception(
            "Failed to warm risk report cache for portfolio %s", portfolio_id
        )


def _register_fund(fund: dict) -> dict:
    save_fund(
        fund["isin"],
        fund["name"],
        fund["security_id"],
        fund.get("performance_id"),
        fund.get("universe"),
        fund.get("ter"),
    )
    try:
        path = download_and_store_fund_nav(
            fund["isin"],
            fund["security_id"],
            start_date=NAV_START_DATE,
            end_date=date.today().isoformat(),
        )
    except DownloadError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    if path is None:
        raise HTTPException(
            status_code=502,
            detail=f"No NAV data returned for {fund['isin']}",
        )
    save_fund_metrics(fund["isin"], compute_fund_metrics(fund["isin"]))
    return {
        "isin": fund["isin"],
        "name": fund["name"],
        "fund_id": fund["security_id"],
        "morningstar_url": morningstar_quote_url(
            fund.get("performance_id"), fund.get("universe")
        ),
    }


def _parse_optional_ter(raw) -> float | None:
    if raw is None or raw == "":
        return None
    try:
        ter = float(raw)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=400, detail="TER must be a number"
        ) from exc
    if ter < 0:
        raise HTTPException(status_code=400, detail="TER cannot be negative")
    return ter


@router.get("/portfolios", response_model=list[PortfolioListItem])
def get_portfolios() -> list[dict]:
    return list_users()


@router.post("/portfolios", response_model=PortfolioListItem, status_code=201)
def add_portfolio(
    body: PortfolioCreate,
    session: Annotated[Session, Depends(get_db)],
) -> dict:
    existing = session.exec(select(User).where(User.name == body.name)).first()
    if existing is not None:
        raise HTTPException(status_code=400, detail="Portfolio name already exists")
    user = User(name=body.name)
    session.add(user)
    session.commit()
    session.refresh(user)
    return {"id": user.id, "name": user.name, "is_default": user.is_default}


@router.delete("/portfolios/{portfolio_id}", status_code=204)
def remove_portfolio(portfolio_id: int) -> None:
    if not delete_user(portfolio_id):
        raise HTTPException(status_code=404, detail="Portfolio not found")
    invalidate_portfolio_risk_reports(portfolio_id)


@router.put("/portfolios/{portfolio_id}/default", response_model=PortfolioListItem)
def mark_default_portfolio(portfolio_id: int) -> dict:
    portfolio = set_default_user(portfolio_id)
    if portfolio is None:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return portfolio


@router.get("/funds", response_model=list[FundResponse])
def get_funds() -> list[dict]:
    return [
        {
            **fund,
            "morningstar_url": morningstar_quote_url(
                fund.get("performance_id"), fund.get("universe")
            ),
        }
        for fund in list_funds()
    ]


@router.post("/funds/import", response_model=FundResponse)
def import_fund_from_morningstar(body: dict) -> dict:
    """Import a fund from a Morningstar legacy-search JSON payload."""
    payload = dict(body)
    ter = _parse_optional_ter(payload.pop("ter", None))
    try:
        fund = parse_morningstar_search(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if ter is not None:
        fund["ter"] = ter
    return _register_fund(fund)


@router.delete("/funds/{isin}", status_code=204)
def remove_fund(isin: str) -> None:
    if not delete_fund(isin.upper()):
        raise HTTPException(status_code=404, detail=f"ISIN {isin} not found")
    delete_fund_nav_csv(isin.upper())
    invalidate_all_risk_reports()


@router.get("/curve")
def get_curve(portfolio_id: int, start_date: date | None = None) -> dict:
    """Buy-and-hold portfolio equity curve from stored NAV files."""
    require_portfolio(portfolio_id)
    return build_user_equity_curve(portfolio_id, start_date=start_date)


@router.get("/metrics")
def get_metrics(portfolio_id: int) -> dict:
    """Portfolio tables with real funds, weights, and stored metrics."""
    require_portfolio(portfolio_id)
    return get_portfolio_metrics(portfolio_id)


@router.get("/positions", response_model=list[PortfolioPositionResponse])
def get_portfolio(portfolio_id: int) -> list[dict]:
    require_portfolio(portfolio_id)
    return list_user_portfolio(portfolio_id)


@router.put("/positions", response_model=list[PortfolioPositionResponse])
def save_portfolio(body: PortfolioSave, portfolio_id: int) -> list[dict]:
    require_portfolio(portfolio_id)
    positions = normalize_portfolio_positions(body.positions)
    saved = save_user_portfolio(portfolio_id, positions)
    _warm_risk_report_cache(portfolio_id)
    return saved
