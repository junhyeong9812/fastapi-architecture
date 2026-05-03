import pytest


@pytest.mark.asyncio
async def test_create_subscription_basic(async_client):
    """Basic 구독 생성 → 201 + is_active=true."""
    response = await async_client.post("/api/v1/subscriptions/", json={
        "customer_name": "홍길동",
        "tier": "basic",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["tier"] == "basic"
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_create_subscription_premium(async_client):
    """Premium 구독 생성."""
    response = await async_client.post("/api/v1/subscriptions/", json={
        "customer_name": "홍길동",
        "tier": "premium",
    })
    assert response.status_code == 201
    assert response.json()["tier"] == "premium"


@pytest.mark.asyncio
async def test_get_subscription(async_client):
    """구독 생성 후 ID로 조회."""
    create_resp = await async_client.post("/api/v1/subscriptions/", json={
        "customer_name": "홍길동",
        "tier": "basic",
    })
    sub_id = create_resp.json()["id"]

    get_resp = await async_client.get(f"/api/v1/subscriptions/{sub_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == sub_id


@pytest.mark.asyncio
async def test_get_active_subscription(async_client):
    """고객명으로 활성 구독 조회."""
    await async_client.post("/api/v1/subscriptions/", json={
        "customer_name": "홍길동",
        "tier": "basic",
    })
    response = await async_client.get("/api/v1/subscriptions/customer/홍길동")
    assert response.status_code == 200
    assert response.json()["customer_name"] == "홍길동"


@pytest.mark.asyncio
async def test_upgrade_expires_old(async_client):
    """★ 핵심 테스트: Basic→Premium 업그레이드 시 기존 Basic 만료."""
    await async_client.post("/api/v1/subscriptions/", json={
        "customer_name": "홍길동",
        "tier": "basic",
    })
    await async_client.post("/api/v1/subscriptions/", json={
        "customer_name": "홍길동",
        "tier": "premium",
    })
    # 활성 구독 조회 → Premium이어야 함 (Basic은 만료됨)
    response = await async_client.get("/api/v1/subscriptions/customer/홍길동")
    assert response.json()["tier"] == "premium"


@pytest.mark.asyncio
async def test_cancel_subscription(async_client):
    """구독 취소."""
    create_resp = await async_client.post("/api/v1/subscriptions/", json={
        "customer_name": "홍길동",
        "tier": "basic",
    })
    sub_id = create_resp.json()["id"]

    cancel_resp = await async_client.post(
        f"/api/v1/subscriptions/{sub_id}/cancel")
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_invalid_tier_returns_error(async_client):
    """존재하지 않는 tier → 에러."""
    response = await async_client.post("/api/v1/subscriptions/", json={
        "customer_name": "홍길동",
        "tier": "diamond",  # 없는 등급
    })
    assert response.status_code in (400, 422, 500)