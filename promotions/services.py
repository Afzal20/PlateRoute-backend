from django.utils import timezone

from common.errors import DomainError
from common.money import bp_of

from .models import Coupon, Redemption


def check(coupon, *, user, subtotal_minor, branch=None):
    """Validate a coupon for (user, basket) and return (discount_minor, free_delivery).

    Domain errors use stable `coupon.<reason>` codes so clients can react.
    """
    now = timezone.now()
    if not coupon.active or not (coupon.starts_at <= now <= coupon.ends_at):
        raise DomainError("coupon.inactive", "This coupon is not available.")
    if coupon.branch and branch and coupon.branch_id != branch.id:
        raise DomainError("coupon.branch_scope", "Coupon is not valid for this restaurant.")
    if subtotal_minor < coupon.min_basket_minor:
        raise DomainError("coupon.min_basket", f"Minimum basket for this coupon is {coupon.min_basket_minor}.")
    if coupon.max_redemptions and Redemption.objects.filter(coupon=coupon).count() >= coupon.max_redemptions:
        raise DomainError("coupon.exhausted", "This coupon has been fully redeemed.")
    if Redemption.objects.filter(coupon=coupon, user=user).count() >= coupon.per_user_limit:
        raise DomainError("coupon.per_user", "You have already used this coupon.")
    if coupon.kind == Coupon.Kind.PERCENT:
        return bp_of(subtotal_minor, coupon.value), False
    if coupon.kind == Coupon.Kind.FIXED:
        return min(coupon.value, subtotal_minor), False
    return 0, True


def get(code):
    return Coupon.objects.filter(code__iexact=(code or "").strip()).first()
