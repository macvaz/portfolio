from fastapi import APIRouter

from portfolio.api.services.macro.schemas import MacroSnapshotResponse
from portfolio.api.services.macro.service import fetch_latest_macro_snapshot

router = APIRouter(prefix="/api/macro", tags=["macro"])


@router.get("", response_model=MacroSnapshotResponse)
def get_macro_snapshot() -> MacroSnapshotResponse:
    """Return the latest macro health series and threshold statuses."""
    return fetch_latest_macro_snapshot()
