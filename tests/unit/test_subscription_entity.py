"""Subscription 엔티티 테스트.

★ DB 없이 순수 Python만으로 테스트.
Orders 모듈과 마찬가지로 domain 레이어는 프레임워크를 모른다.
"""

from datetime import datetime, timedelta, UTC
from re import match

import pytest
from app.subscriptions.domain.entities import (
    Subscription, SubscriptionTier, SubscriptionStatus,
    InvalidSubscriptionError,
)

class TestSubscripttionCreation:
    """구동 생성 규칙 테스트"""
    def test_create_basic(self):
        sub = Subscription.create(customer_name="홍길동", tier=SubscriptionTier.BASIC)
        assert sub.customer_name == "홍길동"
        assert sub.tier == SubscriptionTier.BASIC
        assert sub.status == SubscriptionStatus.ACTIVE
        assert sub.id is not None

    def test_create_premium(self):
        """Premium 구독 정상 생성."""
        sub = Subscription.create(customer_name="홍길동", tier=SubscriptionTier.PREMIUM)
        assert sub.tier == SubscriptionTier.PREMIUM

    def test_create_none_tier_raises(self):
        """NONE 등록으로는 구독 생성 불가. 구독 = 유료만."""
        with pytest.raises(InvalidSubscriptionError, match="등급"):
            Subscription.create(customer_name="홍길동", tier=SubscriptionTier.NONE)

    def test_create_empty_name_raises(self):
        """빈 이름 불가."""
        with pytest.raises(InvalidSubscriptionError, match="이름"):
            Subscription.create(customer_name="", tier=SubscriptionTier.BASIC)

    def test_default_duration_30_days(self):
        """기본 구독 기간은 30일."""
        sub = Subscription.create(customer_name="홍길동", tier=SubscriptionTier.BASIC)
        diff = sub.expires_at - sub.started_at
        assert diff.days == 30

class TestSubscriptionActive:
    """구독 활성 상태 판정 테스트."""

    def test_is_active_when_not_expired(self):
        """만료 전이면 활성."""
        sub = Subscription.create(customer_name="홍길동", tier=SubscriptionTier.BASIC)
        assert sub.is_active() is True

    def test_is_not_active_when_expired(self):
        """duration_days=0이면 즉시 만료"""
        sub = Subscription.create(
            customer_name="홍길동",
            tier=SubscriptionTier.BASIC,
            duration_days=0,
        )
        assert sub.is_active() is False

    def test_is_not_active_when_cancelled(self):
        """취소된 구독은 비활성."""
        sub = Subscription.create(customer_name="홍길동", tier = SubscriptionTier.BASIC)
        sub.cancel()
        assert sub.is_active() is False

class TestSubscriptionStatusChange:
    """구독 상태 변경 테스트."""

    def test_cancel(self):
        """활성 구독 취소."""
        sub = Subscription.create(customer_name="홍길동", tier=SubscriptionTier.BASIC)
        sub.cancel()
        assert sub.status == SubscriptionStatus.CANCELLED

    def test_expire(self):
        """구독 만료 처리. 업그레이드 시 기존 구독을 만료시킬 때 사용."""
        sub = Subscription.create(customer_name="홍길동", tier=SubscriptionTier.BASIC)
        sub.expires()
        assert sub.status == SubscriptionStatus.EXPIRED

    def test_cancel_inactive_raises(self):
        """이미 취소된 구독은 다시 취소 불가."""
        sub = Subscription.create(customer_name="홍길동", tier=SubscriptionTier.BASIC)
        sub.cancel()
        with pytest.raises(InvalidSubscriptionError, match="활성"):
            sub.cancel()