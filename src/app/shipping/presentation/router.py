from uuid import UUID
from fastapi import APIRouter, HTTPException
from dishka.integrations.fastapi import DishkaRoute, FromDishka
from app.shipping.infrastructure.repository import SQLAlchemyShipmentRepository
from app.shipping.application.command_handlers import UpdateShipmentStatusHandler
from app.shipping.application.commands import UpdateShipmentStatusCommand
from app.shipping.presentation.schemas import ShipmentResponse, UpdateStatusRequest

router = APIRouter(prefix="/api/v1/shipping", tags=["Shipping"],
                   route_class=DishkaRoute)


@router.get("/order/{order_id}")
async def get_shipment_by_order(
    order_id: str,
    repo: FromDishka[SQLAlchemyShipmentRepository],
) -> ShipmentResponse:
    shipment = await repo.find_by_order_id(UUID(order_id))
    if shipment is None:
        raise HTTPException(404, "배송 정보가 없습니다")
    return ShipmentResponse(
        id=str(shipment.id), order_id=str(shipment.order_id),
        status=shipment.status.value,
        shipping_fee=float(shipment.shipping_fee.amount),
        original_fee=float(shipment.original_fee.amount),
        fee_discount_type=shipment.fee_discount_type,
        tracking_number=shipment.tracking_number)


@router.post("/{shipment_id}/update-status")
async def update_status(
    shipment_id: str,
    body: UpdateStatusRequest,
    handler: FromDishka[UpdateShipmentStatusHandler],
) -> dict:
    await handler.handle(UpdateShipmentStatusCommand(
        shipment_id=shipment_id, new_status=body.new_status,
        tracking_number=body.tracking_number))
    return {"status": "updated"}