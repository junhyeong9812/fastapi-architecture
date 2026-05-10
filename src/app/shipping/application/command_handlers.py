from uuid import UUID
from datetime import datetime, UTC
from app.shipping.domain.interfaces import ShipmentRepositoryProtocol
from app.shipping.domain.exceptions import ShipmentNotFoundError
from app.shared.event_bus import EventBus
from app.shared.events import ShipmentStatusChangedEvent
from app.shipping.application.commands import UpdateShipmentStatusCommand


class UpdateShipmentStatusHandler:
    def __init__(self, repo: ShipmentRepositoryProtocol, event_bus: EventBus) -> None:
        self._repo = repo
        self._event_bus = event_bus

    async def handle(self, command: UpdateShipmentStatusCommand) -> None:
        shipment = await self._repo.find_by_id(UUID(command.shipment_id))
        if shipment is None:
            raise ShipmentNotFoundError(command.shipment_id)

        if command.new_status == "in_transit":
            shipment.mark_in_transit(command.tracking_number or "TRACK_UNKNOWN")
        elif command.new_status == "delivered":
            shipment.mark_delivered()

        await self._repo.update(shipment)
        await self._event_bus.publish(
            ShipmentStatusChangedEvent(
                shipment_id=shipment.id, order_id=shipment.order_id,
                new_status=command.new_status, timestamp=datetime.now(UTC),
            )
        )