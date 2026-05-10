class ShipmentError(Exception):
    pass

class ShipmentNotFoundError(ShipmentError):
    def __init__(self, shipment_id: str) -> None:
        super().__init__(f"배송을 찾을 수 없습니다: {shipment_id}")