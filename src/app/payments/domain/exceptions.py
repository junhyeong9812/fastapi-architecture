class PaymentError(Exception):
    pass

class PaymentNotFoundError(PaymentError):
    def __init__(self, payment_id: str) -> None:
        super().__init__(f"결제를 찾을 수 없습니다: {payment_id}")

class PaymentGatewayError(PaymentError):
    pass