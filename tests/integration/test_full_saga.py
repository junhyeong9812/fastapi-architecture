"""전체 Saga 흐름: 주문 → 결제 → 배송 → 배송 완료 → tracking 타임라인 확인.

★ 핵심 체감:
하나의 HTTP 요청(POST /orders)이 5개 이상의 도메인 이벤트를 발생시키고,
그 모든 흔적이 tracking 타임라인에 시간순으로 기록된다.
호출 코드 어디에도 모듈 간 직접 참조가 없다.
"""

import pytest


async def _wait_for_tracking(client, order_id: str, max_attempts: int = 10):
    for _ in range(max_attempts):
        resp = await client.get(f"/api/v1/tracking/order/{order_id}")
        if resp.status_code == 200:
            return resp.json()
    return None


@pytest.mark.asyncio
async def test_full_happy_path_records_timeline(async_client):
    """결제 승인된 주문은 tracking에 order.created + payment.approved 기록."""
    # 결제 승인이 보장되도록 여러 번 시도
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
        pytest.skip("FakeGateway 5회 거절 — 매우 드문 케이스")

    tracking = await _wait_for_tracking(async_client, order_id)
    assert tracking is not None

    event_types = [e["event_type"] for e in tracking["events"]]
    assert "order.created" in event_types
    assert "payment.approved" in event_types
    assert "shipment.created" in event_types

    # 타임라인 순서 검증 (order.created가 가장 먼저)
    assert event_types[0] == "order.created"


@pytest.mark.asyncio
async def test_delivered_order_marks_tracking_completed(async_client):
    """배송 delivered → tracking.current_phase=delivered + completed_at 설정."""
    for _ in range(5):
        order_resp = await async_client.post("/api/v1/orders/", json={
            "customer_name": "홍길동",
            "items": [
                {"product_name": "키보드", "quantity": 1, "unit_price": 100000},
            ],
        })
        order_id = order_resp.json()["id"]
        payment = (await async_client.get(
            f"/api/v1/payments/order/{order_id}")).json()
        if payment["status"] == "approved":
            break
    else:
        pytest.skip("FakeGateway 5회 거절")

    # 배송 생성될 때까지 대기
    for _ in range(10):
        s = await async_client.get(f"/api/v1/shipping/order/{order_id}")
        if s.status_code == 200:
            shipment_id = s.json()["id"]
            break
    else:
        pytest.fail("배송이 생성되지 않음")

    # delivered까지 진행
    await async_client.post(
        f"/api/v1/shipping/{shipment_id}/update-status",
        json={"new_status": "in_transit", "tracking_number": "T1"})
    await async_client.post(
        f"/api/v1/shipping/{shipment_id}/update-status",
        json={"new_status": "delivered"})

    tracking = await _wait_for_tracking(async_client, order_id)
    assert tracking is not None
    assert tracking["current_phase"] == "delivered"
    assert tracking["completed_at"] is not None
