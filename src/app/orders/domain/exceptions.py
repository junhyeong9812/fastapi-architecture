"""주문 도메인 예외.

★ 학습 포인트:
도메인 예외는 비즈니스 규칙 위반을 표현한다.
HTTP 상태 코드(400, 404)와는 무관하다.
Presentation 레이어(router)에서 도메인 예외를 HTTP 응답으로 변환한다.
"""

class OrderError(Exception):
    """주문 도메인의 기본 예외. 모든 주문 예외가 이것을 상속"""
    pass

class InvalidOrderError(OrderError):
    """생성 규칙 위반. 빈 이름, 빈 항목, 0 수랑 등."""
    def __init__(self, reason) -> None:
        self.reason = reason
        super().__init__(reason)

class OrderNotFoundError(OrderError):
    """조회 실패. 존재하지 않는 주문 ID."""
    def __init__(self, order_id: str) -> None:
        self.order_id = order_id
        super().__init__(f"주문을 찾을 수 없습니다: {order_id}")

class InvalidStatusTransition(OrderError):
    """상태 전이 규칙 위반. 예: PAID -> CANCELLED 시도."""
    def __init__(self, current: str, target: str) -> None:
        self.current = current
        self.target = target
        super().__init__(f"상태 전이 불가: {current} -> {target}")
