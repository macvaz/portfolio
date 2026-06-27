from portfolio.api.database import get_latest_signals
from portfolio.api.services.signals.schemas import SignalSnapshotResponse


def fetch_latest_signal_snapshot() -> SignalSnapshotResponse:
    snapshot = get_latest_signals()
    if snapshot is None:
        return SignalSnapshotResponse(
            date=None,
            series=[],
            alerts_activated=[],
            alerts_deactivated=[],
        )
    return SignalSnapshotResponse(**snapshot)
