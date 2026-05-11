"""결제 승인 → 배송 자동 생성 흐름 검증."""

import pytest


async def _wait_for_shipment(client, order_id: str, max_attempts: int = 10):
    """배송이 생성될 때까지 폴링. 비동기 이벤트 처리를 기다린다."""
    for _ in range(max_attempts):
        resp = await client.get(f"/api/v1/shipping/order/{order_id}")
        if resp.status_code == 200:
            return resp.json()
    return None


@pytest.mark.asyncio
async def test_payment_approval_creates_shipment(async_client):
    """주문 → 결제 승인 → 배송 자동 생성 (FakeGateway가 승인한 경우만 검증)."""
    order_resp = await async_client.post("/api/v1/orders/", json={
        "customer_name": "홍길동",
        "items": [
            {"product_name": "키보드", "quantity": 1, "unit_price": 100000},
        ],
    })
    order_id = order_resp.json()["id"]

    # 결제가 승인된 경우에만 배송이 생성됨
    payment = (await async_client.get(
        f"/api/v1/payments/order/{order_id}")).json()

    if payment["status"] == "approved":
        shipment = await _wait_for_shipment(async_client, order_id)
        assert shipment is not None
        assert shipment["status"] == "preparing"


@pytest.mark.asyncio
async def test_shipment_status_drives_order_status(async_client):
    """배송 상태 변경 → 주문 상태 자동 전이.

    PREPARING(SHIPPING) → IN_TRANSIT(SHIPPING) → DELIVERED(DELIVERED).
    """
    # 결제 승인이 보장될 때까지 시도 (FakeGateway 90% 승인)
    for _ in range(5):
        order_resp = await async_client.post("/api/v1/orders/", json={
            "customer_name": "홍길동",
            "items": [
                {"product_name": "노트북", "quantity": 1, "unit_price": 100000},
            ],
        })
        order_id = order_resp.json()["id"]
        payment = (await async_client.get(
            f"/api/v1/payments/order/{order_id}")).json()
        if payment["status"] == "approved":
            break
    else:
        pytest.skip("FakeGateway가 5회 모두 거절. 매우 드문 케이스.")

    shipment = await _wait_for_shipment(async_client, order_id)
    assert shipment is not None
    shipment_id = shipment["id"]

    # in_transit으로 변경
    await async_client.post(
        f"/api/v1/shipping/{shipment_id}/update-status",
        json={"new_status": "in_transit", "tracking_number": "T123"},
    )
    order = (await async_client.get(f"/api/v1/orders/{order_id}")).json()
    assert order["status"] == "shipping"

    # delivered로 변경
    await async_client.post(
        f"/api/v1/shipping/{shipment_id}/update-status",
        json={"new_status": "delivered"},
    )
    order = (await async_client.get(f"/api/v1/orders/{order_id}")).json()
    assert order["status"] == "delivered"
