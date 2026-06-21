from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from portfolio.api.database import (
    delete_fund,
    delete_user,
    get_db,
    get_fund,
    get_user,
    init_db,
    list_funds,
    list_user_portfolio,
    list_users,
    save_fund,
    save_user_portfolio,
    set_default_user,
)
from portfolio.finance.nav_files import delete_fund_nav_csv, download_and_store_fund_nav
from portfolio.finance.metrics import refresh_fund_metrics
from portfolio.api.models import User
from portfolio.finance.morningstar import import_isins, morningstar_quote_url
from portfolio.api.curve import build_user_equity_curve
from portfolio.api.metrics import get_portfolio_metrics
from portfolio.api.report import build_report_html, build_user_report_html

WEB_DIR = Path(__file__).resolve().parents[3] / "html"
NAV_START_DATE = "2000-01-01"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Portfolio API", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


class PortfolioCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class PortfolioListItem(BaseModel):
    id: int
    name: str
    is_default: bool = False


class FundCreate(BaseModel):
    isin: str = Field(min_length=12, max_length=12)


class FundResponse(BaseModel):
    isin: str
    name: str
    fund_id: str
    morningstar_url: str | None = None


class PortfolioPosition(BaseModel):
    isin: str = Field(min_length=12, max_length=12)
    weighted_assets: float = Field(gt=0, le=1)


class PortfolioSave(BaseModel):
    positions: list[PortfolioPosition]


class PortfolioPositionResponse(BaseModel):
    isin: str
    name: str
    fund_id: str
    performance_id: str | None = None
    universe: str | None = None
    weighted_assets: float


class ReportRequest(BaseModel):
    positions: list[PortfolioPosition]


def _require_portfolio(portfolio_id: int) -> int:
    if get_user(portfolio_id) is None:
        raise HTTPException(status_code=404, detail=f"Portfolio {portfolio_id} not found")
    return portfolio_id


def _normalize_portfolio_positions(
    positions: list[PortfolioPosition],
) -> list[dict]:
    normalized = []
    for position in positions:
        isin = position.isin.upper()
        if get_fund(isin) is None:
            raise HTTPException(status_code=404, detail=f"Unknown ISIN: {isin}")
        normalized.append({"isin": isin, "weighted_assets": position.weighted_assets})
    return normalized


def _validate_positions(positions: list[PortfolioPosition]) -> list[dict]:
    if not positions:
        raise HTTPException(status_code=400, detail="Portfolio cannot be empty")

    total_weight = sum(position.weighted_assets for position in positions)
    if abs(total_weight - 1.0) > 0.01:
        raise HTTPException(
            status_code=400,
            detail=f"Portfolio weights must sum to 1.0 (got {total_weight:.4f})",
        )

    return _normalize_portfolio_positions(positions)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


@app.get("/api/portfolios", response_model=list[PortfolioListItem])
def get_portfolios() -> list[dict]:
    return list_users()


@app.post("/api/portfolios", response_model=PortfolioListItem, status_code=201)
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


@app.delete("/api/portfolios/{portfolio_id}", status_code=204)
def remove_portfolio(portfolio_id: int) -> None:
    if not delete_user(portfolio_id):
        raise HTTPException(status_code=404, detail="Portfolio not found")


@app.put("/api/portfolios/{portfolio_id}/default", response_model=PortfolioListItem)
def mark_default_portfolio(portfolio_id: int) -> dict:
    portfolio = set_default_user(portfolio_id)
    if portfolio is None:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return portfolio


@app.get("/api/funds", response_model=list[FundResponse])
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


@app.post("/api/funds", response_model=FundResponse)
def create_fund(body: FundCreate) -> dict:
    fund = import_isins(body.isin.upper())
    if fund is None:
        raise HTTPException(
            status_code=404, detail=f"No fund found for ISIN {body.isin}"
        )
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
    refresh_fund_metrics(fund["isin"])
    return {
        "isin": fund["isin"],
        "name": fund["name"],
        "fund_id": fund["security_id"],
        "morningstar_url": morningstar_quote_url(
            fund.get("performance_id"), fund.get("universe")
        ),
    }


@app.delete("/api/funds/{isin}", status_code=204)
def remove_fund(isin: str) -> None:
    if not delete_fund(isin.upper()):
        raise HTTPException(status_code=404, detail=f"ISIN {isin} not found")
    delete_fund_nav_csv(isin.upper())


@app.get("/api/curve")
def get_curve(portfolio_id: int) -> dict:
    """Buy-and-hold portfolio equity curve from stored NAV files."""
    _require_portfolio(portfolio_id)
    return build_user_equity_curve(portfolio_id)


@app.get("/api/metrics")
def get_metrics(portfolio_id: int) -> dict:
    """Portfolio tables with real funds, weights, and stored metrics."""
    _require_portfolio(portfolio_id)
    return get_portfolio_metrics(portfolio_id)


@app.get("/api/portfolio", response_model=list[PortfolioPositionResponse])
def get_portfolio(portfolio_id: int) -> list[dict]:
    _require_portfolio(portfolio_id)
    return list_user_portfolio(portfolio_id)


@app.put("/api/portfolio", response_model=list[PortfolioPositionResponse])
def save_portfolio(body: PortfolioSave, portfolio_id: int) -> list[dict]:
    _require_portfolio(portfolio_id)
    positions = _normalize_portfolio_positions(body.positions)
    return save_user_portfolio(portfolio_id, positions)


@app.get("/api/report", response_class=HTMLResponse)
def get_report(portfolio_id: int) -> HTMLResponse:
    """QuantStats tearsheet for the user's saved portfolio."""
    _require_portfolio(portfolio_id)
    try:
        html = build_user_report_html(portfolio_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return HTMLResponse(content=html)


@app.post("/api/report", response_class=HTMLResponse)
def create_report(body: ReportRequest, portfolio_id: int) -> HTMLResponse:
    _require_portfolio(portfolio_id)
    positions = _validate_positions(body.positions)
    save_user_portfolio(portfolio_id, positions)

    try:
        html = build_report_html(positions)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return HTMLResponse(content=html)


def main() -> None:
    import uvicorn

    uvicorn.run("portfolio.api.app:app", host="0.0.0.0", port=8000, reload=True)
