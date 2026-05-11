"""구독 등급별 배송비 정책 주입 검증.

★ Phase 2의 할인 정책과 완전히 동일한 학습 패턴.
같은 ProcessPaymentHandler/Shipment 코드인데 헤더만 다르면 배송비가 달라진다.
"""

import pytest


async def _create_subscription(client, customer_name: str, tier: str):
    resp = await client.post("/api/v1/subscriptions/", json={
        "customer_name": customer_name, "tier": tier,
    })
    assert resp.status_code == 201


async def _create_order_and_get_shipment(
    client, customer_name: str, amount: int,
):
    """주문 생성 → 결제 승인까지 대기 → 배송 정보 반환.
    결제가 거절되면 None 반환.
    """
    resp = await client.post(
        "/api/v1/orders/",
        json={
            "customer_name": customer_name,
            "items": [
                {"product_name": "상품", "quantity": 1, "unit_price": amount},
            ],
        },
        headers={"X-Customer-Name": customer_name},
    )
    order_id = resp.json()["id"]

    payment = (await client.get(
        f"/api/v1/payments/order/{order_id}")).json()
    if payment["status"] != "approved":
        return None

    for _ in range(10):
        s = await client.get(f"/api/v1/shipping/order/{order_id}")
        if s.status_code == 200:
            return s.json()
    return None


@pytest.mark.asyncio
async def test_premium_always_free(async_client):
    """Premium 구독자: 1,000원 주문도 배송비 0원."""
    await _create_subscription(async_client, "프리미엄", "premium")

    for _ in range(5):
        shipment = await _create_order_and_get_shipment(
            async_client, "프리미엄", 1000)
        if shipment:
            break
    else:
        pytest.skip("FakeGateway 거절 누적")

    assert shipment["shipping_fee"] == 0
    assert shipment["fee_discount_type"] == "premium_free"


@pytest.mark.asyncio
async def test_basic_under_threshold(async_client):
    """Basic 구독자, 3만원 미만: 1,500원 (50% 할인)."""
    await _create_subscription(async_client, "베이직", "basic")

    for _ in range(5):
        shipment = await _create_order_and_get_shipment(
            async_client, "베이직", 20000)
        if shipment:
            break
    else:
        pytest.skip("FakeGateway 거절 누적")

    assert shipment["shipping_fee"] == 1500
    assert shipment["fee_discount_type"] == "basic_half"


@pytest.mark.asyncio
async def test_basic_over_threshold_free(async_client):
    """Basic 구독자, 3만원 이상: 무료배송."""
    await _create_subscription(async_client, "베이직2", "basic")

    for _ in range(5):
        shipment = await _create_order_and_get_shipment(
            async_client, "베이직2", 30000)
        if shipment:
            break
    else:
        pytest.skip("FakeGateway 거절 누적")

    assert shipment["shipping_fee"] == 0


@pytest.mark.asyncio
async def test_standard_under_50000(async_client):
    """미구독, 5만원 미만: 3,000원."""
    for _ in range(5):
        shipment = await _create_order_and_get_shipment(
            async_client, "게스트", 30000)
        if shipment:
            break
    else:
        pytest.skip("FakeGateway 거절 누적")

    assert shipment["shipping_fee"] == 3000
    assert shipment["fee_discount_type"] == "none"


@pytest.mark.asyncio
async def test_standard_over_50000_free(async_client):
    """미구독, 5만원 이상: 무료배송."""
    for _ in range(5):
        shipment = await _create_order_and_get_shipment(
            async_client, "게스트2", 50000)
        if shipment:
            break
    else:
        pytest.skip("FakeGateway 거절 누적")

    assert shipment["shipping_fee"] == 0
