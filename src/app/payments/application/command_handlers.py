from datetime import datetime, UTC
from decimal import Decimal
from uuid import UUID

from app.shared.value_objects import Money
from app.shared.event_bus import EventBus
from app.shared.events import PaymentApprovedEvent, PaymentRejectedEvent
from app.payments.domain.entities import Payment, PaymentMethod
from app.payments.domain.interfaces import (
    DiscountPolicy, PaymentGatewayProtocol, PaymentRepositoryProtocol,
)
from app.payments.application.commands import ProcessPaymentCommand


class ProcessPaymentHandler:
    def __init__(
        self,
        repo: PaymentRepositoryProtocol,
        gateway: PaymentGatewayProtocol,
        discount_policy: DiscountPolicy,        # DI가 구독 등급에 따라 주입
        event_bus: EventBus,
    ) -> None:
        self._repo = repo
        self._gateway = gateway
        self._discount_policy = discount_policy
        self._event_bus = event_bus

    async def handle(self, command: ProcessPaymentCommand) -> UUID:
        amount = Money(command.amount)

        # 정책 적용 — 어떤 정책인지 핸들러는 모른다
        discount = self._discount_policy.calculate_discount(amount)
        final_amount = amount.subtract(discount.discount_amount)

        payment = Payment.create(
            order_id=UUID(command.order_id),
            original_amount=amount,
            discount_amount=discount.discount_amount,
            final_amount=final_amount,
            method=PaymentMethod(command.method),
            applied_discount_type=discount.discount_type,
        )

        # Fake PG 호출 (90% 승인, 10% 거절)
        result = await self._gateway.process(payment)

        if result.success:
            payment.approve(result.transaction_id)
            await self._repo.save(payment)
            await self._event_bus.publish(
                PaymentApprovedEvent(
                    payment_id=payment.id, order_id=payment.order_id,
                    original_amount=payment.original_amount.amount,
                    discount_amount=payment.discount_amount.amount,
                    final_amount=payment.final_amount.amount,
                    applied_discount_type=payment.applied_discount_type,
                    method=payment.method.value,
                    timestamp=datetime.now(UTC),
                )
            )
        else:
            payment.reject(result.message)
            await self._repo.save(payment)
            await self._event_bus.publish(
                PaymentRejectedEvent(
                    payment_id=payment.id, order_id=payment.order_id,
                    reason=result.message,
                    timestamp=datetime.now(UTC),
                )
            )
        return payment.id