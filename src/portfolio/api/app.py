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

from portfolio import generate_performance_report_html
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
    save_user_portfolio,
)
from portfolio.api.models import User
from portfolio import download_portfolio_navs
from portfolio.finance.funds import resolve_fund_by_isin
from portfolio import calculate_buy_and_hold_returns

WEB_DIR = Path(__file__).resolve().parents[3] / "html"


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
    start_date: str = "2025-01-01"
    end_date: str | None = None
    benchmark: str = "SPY"


def _validate_positions(positions: list[PortfolioPosition]) -> list[dict]:
    if not positions:
        raise HTTPException(status_code=400, detail="Portfolio cannot be empty")

    total_weight = sum(position.weighted_assets for position in positions)
    if abs(total_weight - 1.0) > 0.01:
        raise HTTPException(
            status_code=400,
            detail=f"Portfolio weights must sum to 1.0 (got {total_weight:.4f})",
        )

    normalized = []
    for position in positions:
        isin = position.isin.upper()
        if resolve_fund_by_isin(isin) is None:
            raise HTTPException(status_code=404, detail=f"Unknown ISIN: {isin}")
        normalized.append({"isin": isin, "weighted_assets": position.weighted_assets})
    return normalized


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
    return list_funds()


@app.post("/api/funds", response_model=FundResponse)
def create_fund(body: FundCreate, _user: CurrentUser) -> dict:
    fund = resolve_fund_by_isin(body.isin.upper())
    if fund is None:
        raise HTTPException(
            status_code=404, detail=f"No fund found for ISIN {body.isin}"
        )
    return {
        "isin": fund["isin"],
        "name": fund["name"],
        "fund_id": fund["security_id"],
    }


@app.delete("/api/funds/{isin}", status_code=204)
def remove_fund(isin: str, _user: CurrentUser) -> None:
    if not delete_fund(isin.upper()):
        raise HTTPException(status_code=404, detail=f"ISIN {isin} not found")


@app.get("/api/portfolio", response_model=list[PortfolioPositionResponse])
def get_portfolio(user: CurrentUser) -> list[dict]:
    return list_user_portfolio(user.id)


@app.put("/api/portfolio", response_model=list[PortfolioPositionResponse])
def save_portfolio(body: PortfolioSave, user: CurrentUser) -> list[dict]:
    positions = _validate_positions(body.positions)
    return save_user_portfolio(user.id, positions)


@app.post("/api/report", response_class=HTMLResponse)
def create_report(body: ReportRequest, user: CurrentUser) -> HTMLResponse:
    positions = _validate_positions(body.positions)
    portfolio = {
        position["isin"]: position["weighted_assets"] for position in positions
    }
    save_user_portfolio(user.id, positions)

    end_date = body.end_date or date.today().isoformat()
    navs_df = download_portfolio_navs(portfolio, body.start_date, end_date)
    if navs_df.empty:
        raise HTTPException(status_code=400, detail="No NAV data available")

    portfolio_returns_df = calculate_buy_and_hold_returns(navs_df, portfolio)
    html = generate_performance_report_html(portfolio_returns_df, body.benchmark)
    return HTMLResponse(content=html)


def main() -> None:
    import uvicorn

    uvicorn.run("portfolio.api.app:app", host="0.0.0.0", port=8000, reload=True)
