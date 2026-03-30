"""Pydantic v2 Request/Response DTO.

★ 학습 포인트:
Pydantic 모델은 HTTP 요청/응답의 직렬화/역직렬화를 담당한다.
Spring의 @RequestBody, @ResponseBody DTO와 같은 역할.
FastAPI가 자동으로 JSON ↔ Pydantic 변환을 해준다.
"""

from datetime import datetime
from pydantic import BaseModel, Field


class OrderItemRequest(BaseModel):
    """주문 항목 요청. POST /api/v1/orders/ 의 items 배열 원소."""
    product_name: str
    quantity: int = Field(gt=0)         # gt=0: 0보다 커야 함 (>0)
    unit_price: float = Field(gt=0)     # gt=0: 0보다 커야 함


class CreateOrderRequest(BaseModel):
    """주문 생성 요청."""
    customer_name: str
    items: list[OrderItemRequest] = Field(min_length=1)  # 최소 1개


class OrderItemResponse(BaseModel):
    """주문 항목 응답."""
    product_name: str
    quantity: int
    unit_price: float
    subtotal: float                     # 단가 × 수량


class OrderResponse(BaseModel):
    """주문 상세 응답."""
    id: str
    customer_name: str
    status: str
    total_amount: float
    currency: str
    items: list[OrderItemResponse]
    created_at: datetime
    updated_at: datetime


class OrderListResponse(BaseModel):
    """주문 목록 응답 (페이지네이션 포함)."""
    items: list[OrderResponse]
    total: int
    page: int
    size: int