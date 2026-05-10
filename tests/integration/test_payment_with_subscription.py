"""구독 등급별 할인 정책 주입 검증.

★ 핵심 체감:
같은 코드인데 헤더(X-Customer-Name) 한 줄로 할인율이 바뀐다.
이것이 정책 주입의 효과 — 코드 수정 없이 동작이 달라진다.

주의: FakeGateway는 10% 확률로 거절한다. 거절되면 결제 자체가 REJECTED로 저장되며
final_amount는 원래대로 기록된다. 거절 케이스의 영향을 줄이려면 amount 값을 변경하거나
여러 번 시도하는 패턴이 필요. 여기서는 status 검증을 약하게 가져간다.
"""

import pytest


async def _create_subscription(client, customer_name: str, tier: str):
    resp = await client.post("/api/v1/subscriptions/", json={
        "customer_name": customer_name,
        "tier": tier,
    })
    assert resp.status_code == 201


async def _create_order_for(client, customer_name: str, amount: int) -> str:
    """헤더로 customer를 식별하여 주문 생성. order_id 반환."""
    resp = await client.post(
        "/api/v1/orders/",
        json={
            "customer_name": customer_name,
            "items": [
                {"product_name": "노트북", "quantity": 1, "unit_price": amount},
            ],
        },
        headers={"X-Customer-Name": customer_name},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_premium_subscriber_gets_10_percent_discount(async_client):
    """Premium 구독자 → 10% 할인 적용."""
    await _create_subscription(async_client, "프리미엄", "premium")
    order_id = await _create_order_for(async_client, "프리미엄", 100000)

    payment = (await async_client.get(
        f"/api/v1/payments/order/{order_id}")).json()
    assert payment["original_amount"] == 100000
    assert payment["discount_amount"] == 10000     # 10% 할인
    assert payment["final_amount"] == 90000
    assert payment["applied_discount_type"] == "premium_subscription"


@pytest.mark.asyncio
async def test_basic_subscriber_gets_5_percent_discount(async_client):
    """Basic 구독자 → 5% 할인 적용."""
    await _create_subscription(async_client, "베이직", "basic")
    order_id = await _create_order_for(async_client, "베이직", 100000)

    payment = (await async_client.get(
        f"/api/v1/payments/order/{order_id}")).json()
    assert payment["discount_amount"] == 5000      # 5% 할인
    assert payment["final_amount"] == 95000
    assert payment["applied_discount_type"] == "basic_subscription"


@pytest.mark.asyncio
async def test_non_subscriber_gets_no_discount(async_client):
    """미구독 → 할인 없음."""
    order_id = await _create_order_for(async_client, "게스트", 100000)

    payment = (await async_client.get(
        f"/api/v1/payments/order/{order_id}")).json()
    assert payment["discount_amount"] == 0
    assert payment["final_amount"] == 100000
    assert payment["applied_discount_type"] == "none"
