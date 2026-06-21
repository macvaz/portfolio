from fastapi import APIRouter

router = APIRouter(prefix="/api/signals", tags=["signals"])


@router.get("")
def list_signals() -> dict:
    """Return tactical macro and market signals."""
    return {}
