from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from portfolio.api.services.categories.service import fetch_top_categories
from portfolio.storage.database import get_db

router = APIRouter(prefix="/api/categories", tags=["categories"])


@router.get("/ranking")
def get_category_ranking(
    session: Session = Depends(get_db),
    limit: int | None = Query(default=None, ge=1),
) -> dict:
    """Category ranking with multi-horizon monthly returns."""
    return fetch_top_categories(session, limit=limit)
