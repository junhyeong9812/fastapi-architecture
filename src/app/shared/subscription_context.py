"""구독 상태를 요약한 불변 DTO.

★ 학습 포인트 (횡단 관심사 설계):

문제: Payments 모듈이 "이 고객이 Premium인지" 알아야 할인을 적용한다.
     그렇다고 Payments가 Subscriptions를 import하면 모듈 간 결합이 생긴다.

해결: shared에 얇은 DTO를 두고, DI 컨테이너가 중개한다.
  1. DI 컨테이너가 Subscriptions 모듈에서 고객의 구독 상태를 조회
  2. 이 DTO(SubscriptionContext)로 변환
  3. Payments에 주입

결과: Payments는 Subscription 엔티티를 모른다. 이 DTO만 안다.
     Subscriptions도 Payments를 모른다.
     모듈 간 직접 의존이 0.
"""

from dataclasses import dataclass

@dataclass(frozen = True) # frozen=True: 생성 후 값 변경 불가 (불변 객체)
class SubscriptionContext():
    customer_name: str
    tier: str   # "none", "basic", "premium"
    is_active: bool

    @classmethod
    def guest(cls, customer_name: str = "guest") -> "SubscriptionContext":
        """미구독 고객용 기본값, 구독이 없는 고객은 tier= "none"."""
        return cls(customer_name=customer_name, tier="none", is_active=False)