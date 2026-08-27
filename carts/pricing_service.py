"""PricingService (FR-CART-03) — the only place money math lives (§4 rule 4).

All amounts are integer minor units (DR-005). Percentages round half-up per
step via common.money.bp_of. Invariants asserted by property-style tests:
grand_total == items_total - discount + delivery + vat + tip, never negative.
VAT applies to the discounted items subtotal.
"""
from common.money import bp_of

DEFAULT_VAT_BP = 500  # 5% — overridden via RuntimeConfig "pricing.vat_bp"


def quote(*, lines, coupon=None, delivery_fee_minor, tip_minor=0, vat_bp=DEFAULT_VAT_BP):
    """Build the PriceBreakdown from cart lines and an optional coupon result.

    lines: iterable of dicts with a `line_total_minor` key (frozen cart lines).
    coupon: optional (discount_minor, free_delivery) tuple from promotions.
    """
    items_total = sum(int(line["line_total_minor"]) for line in lines)
    discount, free_delivery = coupon if coupon else (0, False)
    delivery_fee = 0 if free_delivery else delivery_fee_minor
    vat = bp_of(max(items_total - discount, 0), vat_bp)
    breakdown = {
        "items_total_minor": items_total,
        "discount_minor": discount,
        "delivery_fee_minor": delivery_fee,
        "vat_minor": vat,
        "vat_bp": vat_bp,
        "tip_minor": tip_minor,
        "grand_total_minor": items_total - discount + delivery_fee + vat + tip_minor,
    }
    return {**breakdown, "grand_total_minor": max(breakdown["grand_total_minor"], 0)}
