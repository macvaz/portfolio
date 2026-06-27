from fastapi import APIRouter

from portfolio.api.services.signals.schemas import SignalSnapshotResponse
from portfolio.api.services.signals.service import fetch_latest_signal_snapshot

router = APIRouter(prefix="/api/signals", tags=["signals"])


@router.get("", response_model=SignalSnapshotResponse)
def list_signals() -> SignalSnapshotResponse:
    """Return the latest computed tactical signals."""
    return fetch_latest_signal_snapshot()
