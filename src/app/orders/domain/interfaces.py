"""Repository 인터페이스 (Output Port).

★ 학습 포인트 (Hexagonal Architecture):
이것은 "포트(Port)"이다. 도메인이 외부에 요구하는 인터페이스.
실제 구현(Adapter)은 infrastructure 레이어에 있다.

Protocol: Python의 구조적 서브타이핑.
  - Java의 interface와 비슷하지만, 명시적 implements가 필요 없다.
  - 같은 메서드 시그니처를 가지면 자동으로 Protocol을 충족한다 (duck typing).

Command(쓰기)와 Query(읽기)를 분리한 이유:
  - Command 핸들러는 OrderRepositoryProtocol만 의존 → save, update
  - Query 핸들러는 OrderReadRepositoryProtocol만 의존 → find, list
  - Phase 1에서는 같은 구현체가 둘 다 충족하지만, 나중에 분리 가능
"""

from typing import Protocol
from uuid import UUID
from app.orders.domain.entities import Order

class OrderRepositoryProtocol(Protocol):
    """쓰기용 Repository, Command 핸들러가 의존."""
    async def save(self, order: Order) -> None:...
    async def find_by_id(self, order_id: UUID) -> Order | None:...
    async def update(self, order: Order) -> None: ...

class OrderReadRepositoryProtocol(Protocol):
    """읽기용 Repository, Query 핸들러가 의존."""
    async def find_by_id(self, order_id: UUID) -> Order | None:...
    async def list_orders(
        self,
        customer_name: str | None = None,
        status: str | None = None,
        page: int = 1,
        size: int = 20.
    ) -> list[Order]:...
    async def count_orders(
        self,
        customer_name: str | None = None,
        status: str | None = None,
    ) -> int: ...