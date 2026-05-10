class TrackingNotFoundError(Exception):
    def __init__(self, order_id: str) -> None:
        super().__init__(f"추적 정보를 찾을 수 없습니다: {order_id}")