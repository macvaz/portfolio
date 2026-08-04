from pydantic import BaseModel

from portfolio.api.services.management.schemas import PortfolioPosition


class RiskReportRequest(BaseModel):
    positions: list[PortfolioPosition]
