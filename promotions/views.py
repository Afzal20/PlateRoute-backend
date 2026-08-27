from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .models import Coupon


class CouponValidateView(APIView):
    """POST {code, subtotal_minor} -> discount preview (FR-CART-04)."""

    def post(self, request):
        coupon = get_object_or_404(Coupon, code__iexact=request.data.get("code", "").strip())
        discount, free_delivery = services.check(
            coupon, user=request.user, subtotal_minor=int(request.data.get("subtotal_minor", 0)),
        )
        return Response({"code": coupon.code, "kind": coupon.kind,
                         "discount_minor": discount, "free_delivery": free_delivery})
