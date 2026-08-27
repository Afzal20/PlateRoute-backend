"""§4 rule 5: order transitions are legal only through this map (FR-ORD docs).

Courier-side movement (picked/out/delivered) is driven by the delivery app
through orders.services.transition; nothing else mutates order.status.
"""

TRANSITIONS = {
    "placed": {"accepted", "rejected", "cancelled_customer", "failed_payment", "cancelled_platform"},
    "accepted": {"preparing", "cancelled_customer", "cancelled_restaurant", "cancelled_platform"},
    "preparing": {"ready", "cancelled_customer", "cancelled_restaurant", "cancelled_platform"},
    "ready": {"picked", "cancelled_restaurant", "cancelled_platform"},
    "picked": {"out", "delivered", "cancelled_platform"},
    "out": {"delivered", "cancelled_platform"},
    "delivered": {"refund_pending"},
    "rejected": {"refund_pending", "refunded"},
    "cancelled_customer": {"refund_pending"},
    "cancelled_restaurant": {"refund_pending"},
    "cancelled_platform": {"refund_pending"},
    "failed_payment": {"refunded"},
    "refund_pending": {"refunded"},
}

TERMINAL = {"rejected", "cancelled_customer", "cancelled_restaurant", "cancelled_platform",
            "failed_payment", "refunded"}


def can(current, to_status):
    return to_status in TRANSITIONS.get(current, set())
