from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from common.errors import DomainError

from . import services
from .models import Coupon


def _positive_int(value, default=0):
    try:
        return max(int(value), 0)
    except (TypeError, ValueError):
        raise DomainError("coupon.bad_subtotal", "subtotal_minor must be an integer.", status.HTTP_400_BAD_REQUEST)


class CouponValidateView(APIView):
    """POST {code, subtotal_minor} -> discount preview (FR-CART-04)."""

    def post(self, request):
        code = (request.data.get("code") or "").strip()
        coupon = services.get(code)
        if coupon is None:
            raise DomainError("coupon.unknown", "Unknown coupon code.", status.HTTP_404_NOT_FOUND)
        discount, free_delivery = services.check(coupon, user=request.user,
                                                 subtotal_minor=_positive_int(request.data.get("subtotal_minor")))
        return Response({"code": coupon.code, "kind": coupon.kind,
                         "discount_minor": discount, "free_delivery": free_delivery})
