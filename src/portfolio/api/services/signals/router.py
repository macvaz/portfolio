from fastapi import APIRouter

from portfolio.api.services.signals.service import get_signals

router = APIRouter(prefix="/api/signals", tags=["signals"])


@router.get("")
def list_signals() -> dict:
    """Return tactical macro and market signals."""
    return get_signals()
