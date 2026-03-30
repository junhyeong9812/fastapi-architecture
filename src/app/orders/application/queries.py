"""Query DTO — 읽기 의도를 표현한다.

★ CQRS 포인트:
Query 핸들러는 EventBus가 없다.
읽기는 부수효과(이벤트 발행, DB 변경) 없이 데이터만 반환한다.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class GetOrderQuery:
    """단건 주문 조회."""
    order_id: str


@dataclass(frozen=True)
class ListOrdersQuery:
    """주문 목록 조회 (페이지네이션 + 필터)."""
    customer_name: str | None = None    # 고객명 필터
    status: str | None = None           # 상태 필터
    page: int = 1
    size: int = 20