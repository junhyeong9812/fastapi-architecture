"""주문 → 이벤트 → 자동 결제 흐름 검증.

★ 핵심 체감:
HTTP 요청은 POST /api/v1/orders 하나뿐인데
이벤트 버스를 통해 결제까지 자동으로 이어진다.
호출 코드 어디에도 Payments를 import한 흔적이 없다.
"""

import pytest


@pytest.mark.asyncio
async def test_order_triggers_payment_creation(async_client):
    """주문 생성 → 자동으로 Payment가 생성되어 조회 가능."""
    # 1. 주문 생성 (헤더 없음 → 미구독으로 처리)
    order_resp = await async_client.post("/api/v1/orders/", json={
        "customer_name": "홍길동",
        "items": [
            {"product_name": "키보드", "quantity": 1, "unit_price": 100000},
        ],
    })
    assert order_resp.status_code == 201
    order_id = order_resp.json()["id"]

    # 2. 결제가 자동으로 생성되었는지 확인
    payment_resp = await async_client.get(f"/api/v1/payments/order/{order_id}")
    assert payment_resp.status_code == 200
    payment = payment_resp.json()

    # 3. 미구독 → 할인 0원
    assert payment["original_amount"] == 100000
    assert payment["discount_amount"] == 0
    assert payment["final_amount"] == 100000
    assert payment["applied_discount_type"] == "none"


@pytest.mark.asyncio
async def test_payment_status_is_terminal(async_client):
    """결제 상태는 approved 또는 rejected (FakeGateway 90/10)."""
    order_resp = await async_client.post("/api/v1/orders/", json={
        "customer_name": "홍길동",
        "items": [
            {"product_name": "키보드", "quantity": 1, "unit_price": 50000},
        ],
    })
    order_id = order_resp.json()["id"]

    payment = (await async_client.get(
        f"/api/v1/payments/order/{order_id}")).json()
    assert payment["status"] in ("approved", "rejected")
