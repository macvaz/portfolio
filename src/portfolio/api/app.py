from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, Field
from sqlmodel import Session

from portfolio.api.auth import (
    CurrentUser,
    authenticate_user,
    create_access_token,
    get_user_by_email,
    hash_password,
)
from portfolio.api.database import (
    delete_fund,
    get_db,
    init_db,
    list_funds,
    list_user_portfolio,
    save_fund,
    save_user_portfolio,
)
from portfolio.finance.nav_files import delete_fund_nav_csv, download_and_store_fund_nav
from portfolio.finance.metrics import refresh_fund_metrics
from portfolio.api.models import User
from portfolio.finance.funds import morningstar_quote_url, resolve_fund_by_isin
from portfolio.api.curve import build_user_equity_curve
from portfolio.api.mock_management import build_dashboard_data
from portfolio.api.report import build_report_html, build_user_report_html

WEB_DIR = Path(__file__).resolve().parents[3] / "html"
NAV_START_DATE = "2000-01-01"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Portfolio API", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class UserResponse(BaseModel):
    id: int
    email: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


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
    weighted_assets: float


class ReportRequest(BaseModel):
    positions: list[PortfolioPosition]


def _normalize_portfolio_positions(
    positions: list[PortfolioPosition],
) -> list[dict]:
    normalized = []
    for position in positions:
        isin = position.isin.upper()
        if resolve_fund_by_isin(isin) is None:
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


@app.post("/api/auth/register", response_model=UserResponse, status_code=201)
def register(
    body: UserRegister,
    session: Annotated[Session, Depends(get_db)],
) -> User:
    if get_user_by_email(session, body.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(email=body.email, hashed_password=hash_password(body.password))
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@app.post("/api/auth/token", response_model=TokenResponse)
def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Annotated[Session, Depends(get_db)],
) -> TokenResponse:
    user = authenticate_user(session, form.username, form.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenResponse(access_token=create_access_token(user.email))


@app.get("/api/auth/me", response_model=UserResponse)
def me(user: CurrentUser) -> User:
    return user


@app.get("/api/funds", response_model=list[FundResponse])
def get_funds(_user: CurrentUser) -> list[dict]:
    return [
        {
            **fund,
            "morningstar_url": morningstar_quote_url(fund.get("performance_id")),
        }
        for fund in list_funds()
    ]


@app.post("/api/funds", response_model=FundResponse)
def create_fund(body: FundCreate, _user: CurrentUser) -> dict:
    fund = resolve_fund_by_isin(body.isin.upper())
    if fund is None:
        raise HTTPException(
            status_code=404, detail=f"No fund found for ISIN {body.isin}"
        )
    save_fund(
        fund["isin"],
        fund["name"],
        fund["security_id"],
        fund.get("performance_id"),
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
        "morningstar_url": morningstar_quote_url(fund.get("performance_id")),
    }


@app.delete("/api/funds/{isin}", status_code=204)
def remove_fund(isin: str, _user: CurrentUser) -> None:
    if not delete_fund(isin.upper()):
        raise HTTPException(status_code=404, detail=f"ISIN {isin} not found")
    delete_fund_nav_csv(isin.upper())


@app.get("/api/curve")
def get_curve(user: CurrentUser) -> dict:
    """Buy-and-hold portfolio equity curve from stored NAV files."""
    return build_user_equity_curve(user.id)


@app.get("/api/dashboard")
def get_dashboard(user: CurrentUser) -> dict:
    """Portfolio tables with real funds, weights, and stored metrics."""
    return build_dashboard_data(user.id)


@app.get("/api/portfolio", response_model=list[PortfolioPositionResponse])
def get_portfolio(user: CurrentUser) -> list[dict]:
    return list_user_portfolio(user.id)


@app.put("/api/portfolio", response_model=list[PortfolioPositionResponse])
def save_portfolio(body: PortfolioSave, user: CurrentUser) -> list[dict]:
    positions = _normalize_portfolio_positions(body.positions)
    return save_user_portfolio(user.id, positions)


@app.get("/api/report", response_class=HTMLResponse)
def get_report(user: CurrentUser) -> HTMLResponse:
    """QuantStats tearsheet for the user's saved portfolio."""
    try:
        html = build_user_report_html(user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return HTMLResponse(content=html)


@app.post("/api/report", response_class=HTMLResponse)
def create_report(body: ReportRequest, user: CurrentUser) -> HTMLResponse:
    positions = _validate_positions(body.positions)
    save_user_portfolio(user.id, positions)

    try:
        html = build_report_html(positions)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return HTMLResponse(content=html)


def main() -> None:
    import uvicorn

    uvicorn.run("portfolio.api.app:app", host="0.0.0.0", port=8000, reload=True)
