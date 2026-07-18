from fastapi import HTTPException
from pydantic import BaseModel, Field

from portfolio.api.database import get_fund, get_user


class PortfolioCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class PortfolioListItem(BaseModel):
    id: int
    name: str
    is_default: bool = False


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


class RiskReportRequest(BaseModel):
    positions: list[PortfolioPosition]


def require_portfolio(portfolio_id: int) -> int:
    if get_user(portfolio_id) is None:
        raise HTTPException(
            status_code=404, detail=f"Portfolio {portfolio_id} not found"
        )
    return portfolio_id


def normalize_portfolio_positions(positions: list[PortfolioPosition]) -> list[dict]:
    normalized = []
    for position in positions:
        isin = position.isin.upper()
        if get_fund(isin) is None:
            raise HTTPException(status_code=404, detail=f"Unknown ISIN: {isin}")
        normalized.append({"isin": isin, "weighted_assets": position.weighted_assets})
    return normalized


def validate_positions(positions: list[PortfolioPosition]) -> list[dict]:
    if not positions:
        raise HTTPException(status_code=400, detail="Portfolio cannot be empty")

    total_weight = sum(position.weighted_assets for position in positions)
    if abs(total_weight - 1.0) > 0.01:
        raise HTTPException(
            status_code=400,
            detail=f"Portfolio weights must sum to 1.0 (got {total_weight:.4f})",
        )

    return normalize_portfolio_positions(positions)
