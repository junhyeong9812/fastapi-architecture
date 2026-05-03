import pytest


@pytest.mark.asyncio
async def test_create_order_success(async_client):
    """주문 생성 → 201 + 상태 payment_pending."""
    response = await async_client.post("/api/v1/orders/", json={
        "customer_name": "홍길동",
        "items": [
            {"product_name": "키보드", "quantity": 1, "unit_price": 150000}
        ],
    })
    assert response.status_code == 201
    data = response.json()
    assert data["customer_name"] == "홍길동"
    assert data["status"] == "payment_pending"  # 생성 즉시 결제 대기
    assert float(data["total_amount"]) == 150000


@pytest.mark.asyncio
async def test_create_order_multiple_items(async_client):
    """복수 항목 주문 → 총액 자동 계산."""
    response = await async_client.post("/api/v1/orders/", json={
        "customer_name": "홍길동",
        "items": [
            {"product_name": "키보드", "quantity": 2, "unit_price": 150000},
            {"product_name": "마우스", "quantity": 1, "unit_price": 50000},
        ],
    })
    assert response.status_code == 201
    # 150000×2 + 50000×1 = 350000
    assert float(response.json()["total_amount"]) == 350000


@pytest.mark.asyncio
async def test_create_order_empty_items_returns_422(async_client):
    """빈 항목 → Pydantic 검증 실패 → 422."""
    response = await async_client.post("/api/v1/orders/", json={
        "customer_name": "홍길동",
        "items": [],
    })
    assert response.status_code == 422  # Pydantic min_length=1 위반


@pytest.mark.asyncio
async def test_get_order(async_client):
    """주문 생성 후 ID로 조회."""
    create_resp = await async_client.post("/api/v1/orders/", json={
        "customer_name": "홍길동",
        "items": [
            {"product_name": "키보드", "quantity": 1, "unit_price": 150000}
        ],
    })
    order_id = create_resp.json()["id"]

    get_resp = await async_client.get(f"/api/v1/orders/{order_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == order_id


@pytest.mark.asyncio
async def test_get_order_not_found(async_client):
    """존재하지 않는 ID → 404."""
    response = await async_client.get(
        "/api/v1/orders/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_orders(async_client):
    """주문 생성 후 목록 조회."""
    await async_client.post("/api/v1/orders/", json={
        "customer_name": "홍길동",
        "items": [
            {"product_name": "키보드", "quantity": 1, "unit_price": 150000}
        ],
    })
    response = await async_client.get("/api/v1/orders/")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_cancel_order(async_client):
    """주문 생성 → 취소 → 상태 cancelled."""
    create_resp = await async_client.post("/api/v1/orders/", json={
        "customer_name": "홍길동",
        "items": [
            {"product_name": "키보드", "quantity": 1, "unit_price": 150000}
        ],
    })
    order_id = create_resp.json()["id"]

    cancel_resp = await async_client.post(f"/api/v1/orders/{order_id}/cancel")
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "cancelled"