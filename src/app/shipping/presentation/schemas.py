from pydantic import BaseModel


class ShipmentResponse(BaseModel):
    id: str
    order_id: str
    status: str
    shipping_fee: float
    original_fee: float
    fee_discount_type: str
    tracking_number: str | None


class UpdateStatusRequest(BaseModel):
    new_status: str
    tracking_number: str | None = None