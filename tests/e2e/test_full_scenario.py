"""전체 시나리오 E2E 테스트 (Phase 6)."""

import pytest


@pytest.mark.asyncio
async def test_full_happy_path(async_client):
    """구독 → 주문 → (이벤트로 자동 결제/배송) → 상태 확인."""
    # 1. Premium 구독
    sub_resp = await async_client.post("/api/v1/subscriptions/", json={
        "customer_name": "홍길동", "tier": "premium"})
    assert sub_resp.status_code == 201

    # 2. 주문
    order_resp = await async_client.post("/api/v1/orders/", json={
        "customer_name": "홍길동",
        "items": [{"product_name": "노트북", "quantity": 1, "unit_price": 1500000}],
    })
    assert order_resp.status_code == 201
    order_id = order_resp.json()["id"]

    # 3. 상태 확인
    get_resp = await async_client.get(f"/api/v1/orders/{order_id}")
    assert get_resp.json()["status"] == "payment_pending"


@pytest.mark.asyncio
async def test_cancel_order(async_client):
    """주문 취소 흐름."""
    order_resp = await async_client.post("/api/v1/orders/", json={
        "customer_name": "박영희",
        "items": [{"product_name": "마우스", "quantity": 1, "unit_price": 50000}],
    })
    order_id = order_resp.json()["id"]

    cancel_resp = await async_client.post(f"/api/v1/orders/{order_id}/cancel")
    assert cancel_resp.json()["status"] == "cancelled"
