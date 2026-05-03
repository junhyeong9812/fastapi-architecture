import asyncio
import random
import uuid
from app.payments.domain.interfaces import GatewayResult


class FakePaymentGateway:
    async def process(self, payment) -> GatewayResult:
        await asyncio.sleep(0.1)    # 네트워크 지연 시뮬레이션
        if random.random() < 0.9:   # 90% 승인
            return GatewayResult(
                success=True,
                transaction_id=f"txn_{uuid.uuid4().hex[:12]}",
                message="승인",
            )
        return GatewayResult(       # 10% 거절
            success=False,
            transaction_id=None,
            message="잔액 부족",
        )