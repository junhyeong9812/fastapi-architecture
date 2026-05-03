from app.shared.events import OrderCreatedEvent
from app.payments.application.commands import ProcessPaymentCommand
from app.payments.application.command_handlers import ProcessPaymentHandler


async def handle_order_created(
    event: OrderCreatedEvent,
    handler: ProcessPaymentHandler,
) -> None:
    await handler.handle(
        ProcessPaymentCommand(
            order_id=str(event.order_id),
            amount=event.total_amount,
            customer_name=event.customer_name,
            method="credit_card",
        )
    )