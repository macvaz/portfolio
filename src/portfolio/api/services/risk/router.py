from datetime import date
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from portfolio.api.services.management.schemas import (
    require_portfolio,
    validate_positions,
)
from portfolio.api.services.risk.risk_report import (
    build_risk_report_html,
    build_user_risk_report_html,
)
from portfolio.api.services.risk.risk_report_cache import write_cached_risk_report
from portfolio.api.services.risk.schemas import RiskReportRequest
from portfolio.storage.database import save_user_portfolio

router = APIRouter(prefix="/api/portfolio", tags=["risk"])
logger = logging.getLogger(__name__)


@router.get("/risk_report", response_class=HTMLResponse)
def get_risk_report(portfolio_id: int, start_date: date | None = None) -> HTMLResponse:
    """QuantStats tearsheet for the user's saved portfolio."""
    require_portfolio(portfolio_id)
    try:
        html = build_user_risk_report_html(portfolio_id, start_date=start_date)
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
    write_cached_risk_report(portfolio_id, positions, html)
    return HTMLResponse(content=html)
