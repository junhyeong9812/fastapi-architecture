from uuid import UUID
from app.tracking.domain.entities import OrderTracking
from app.tracking.domain.exceptions import TrackingNotFoundError
from app.tracking.domain.interfaces import TrackingRepositoryProtocol
from app.tracking.application.queries import GetOrderTrackingQuery


class GetOrderTrackingHandler:
    def __init__(self, repo: TrackingRepositoryProtocol) -> None:
        self._repo = repo

    async def handle(self, query: GetOrderTrackingQuery) -> OrderTracking:
        tracking = await self._repo.find_by_order_id(UUID(query.order_id))
        if tracking is None:
            raise TrackingNotFoundError(query.order_id)
        return tracking