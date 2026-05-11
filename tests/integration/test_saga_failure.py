"""결제 거절 시 보상 흐름: 주문 자동 취소 + tracking phase=FAILED.

★ 핵심 체감:
하나의 핸들러(payment) 결과가 다른 핸들러(orders)의 보상 트랜잭션을 트리거한다.
모듈 간 직접 호출 없이, PaymentRejectedEvent라는 사실(fact)만 공유된다.

FakeGateway는 random이라 거절을 강제할 수 없다.
거절을 보장하려면 monkeypatch로 FakeGateway.process를 항상 거절하도록 패치하는 패턴이 일반적이다.
"""

import pytest
from unittest.mock import patch

from app.payments.domain.interfaces import GatewayResult


@pytest.mark.asyncio
async def test_payment_rejection_cancels_order_and_marks_failed(async_client):
    """FakeGateway를 거절로 강제 → 주문 CANCELLED + tracking FAILED."""

    async def always_reject(self, payment) -> GatewayResult:
        return GatewayResult(
            success=False, transaction_id=None, message="강제 거절 (테스트)")

    with patch(
        "app.payments.infrastructure.fake_gateway.FakePaymentGateway.process",
        always_reject,
    ):
        order_resp = await async_client.post("/api/v1/orders/", json={
            "customer_name": "홍길동",
            "items": [
                {"product_name": "키보드", "quantity": 1, "unit_price": 100000},
            ],
        })
        order_id = order_resp.json()["id"]

        # 주문 자동 취소 확인
        order = (await async_client.get(f"/api/v1/orders/{order_id}")).json()
        assert order["status"] == "cancelled"

        # tracking phase=failed
        tracking = (await async_client.get(
            f"/api/v1/tracking/order/{order_id}")).json()
        assert tracking["current_phase"] == "failed"

        event_types = [e["event_type"] for e in tracking["events"]]
        assert "payment.rejected" in event_types
