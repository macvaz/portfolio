from fastapi import APIRouter

from portfolio.api.services.alerts.schemas import AlertSnapshotResponse
from portfolio.api.services.alerts.service import fetch_latest_alert_snapshot

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("", response_model=AlertSnapshotResponse)
def list_alerts() -> AlertSnapshotResponse:
    """Return the latest tactical macro series and alert statuses."""
    return fetch_latest_alert_snapshot()
