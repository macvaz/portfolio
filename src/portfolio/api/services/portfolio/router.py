from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select

from portfolio.api.database import (
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
from portfolio.api.models import User
from portfolio.api.services.portfolio.curve import build_user_equity_curve
from portfolio.api.services.portfolio.metrics import get_portfolio_metrics
from portfolio.api.services.portfolio.risk_report import (
    build_risk_report_html,
    build_user_risk_report_html,
)
from portfolio.api.services.portfolio.schemas import (
    FundResponse,
    PortfolioCreate,
    PortfolioListItem,
    PortfolioPositionResponse,
    PortfolioSave,
    RiskReportRequest,
    normalize_portfolio_positions,
    require_portfolio,
    validate_positions,
)
from portfolio.datasources.morningstar import (
    morningstar_quote_url,
    parse_morningstar_search,
)
from portfolio.common.metrics import compute_fund_metrics
from portfolio.common.navs import delete_fund_nav_csv, download_and_store_fund_nav

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])
NAV_START_DATE = "2000-01-01"


def _register_fund(fund: dict) -> dict:
    save_fund(
        fund["isin"],
        fund["name"],
        fund["security_id"],
        fund.get("performance_id"),
        fund.get("universe"),
    )
    download_and_store_fund_nav(
        fund["isin"],
        fund["security_id"],
        start_date=NAV_START_DATE,
        end_date=date.today().isoformat(),
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
    try:
        fund = parse_morningstar_search(body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _register_fund(fund)


@router.delete("/funds/{isin}", status_code=204)
def remove_fund(isin: str) -> None:
    if not delete_fund(isin.upper()):
        raise HTTPException(status_code=404, detail=f"ISIN {isin} not found")
    delete_fund_nav_csv(isin.upper())


@router.get("/curve")
def get_curve(portfolio_id: int) -> dict:
    """Buy-and-hold portfolio equity curve from stored NAV files."""
    require_portfolio(portfolio_id)
    return build_user_equity_curve(portfolio_id)


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
    return save_user_portfolio(portfolio_id, positions)


@router.get("/risk_report", response_class=HTMLResponse)
def get_risk_report(portfolio_id: int) -> HTMLResponse:
    """QuantStats tearsheet for the user's saved portfolio."""
    require_portfolio(portfolio_id)
    try:
        html = build_user_risk_report_html(portfolio_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return HTMLResponse(content=html)


@router.post("/risk_report", response_class=HTMLResponse)
def create_risk_report(body: RiskReportRequest, portfolio_id: int) -> HTMLResponse:
    require_portfolio(portfolio_id)
    positions = validate_positions(body.positions)
    save_user_portfolio(portfolio_id, positions)

    try:
        html = build_risk_report_html(positions)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return HTMLResponse(content=html)
