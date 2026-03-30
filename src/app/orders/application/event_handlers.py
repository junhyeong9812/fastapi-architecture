"""외부 이벤트 수신 핸들러.

Phase 1에서는 빈 파일. 자리만 마련해둔다.
Phase 2에서 PaymentApprovedEvent → order.mark_paid() 추가.
Phase 3에서 ShipmentCreatedEvent → order.mark_shipping() 추가.
"""