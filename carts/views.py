from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from common.errors import DomainError
from common.models import RuntimeConfig
from menus.models import Item
from promotions import services as promo
from promotions.services import get as get_coupon

from . import services
from .models import Cart, CartItem
from .pricing_service import quote
from .serializers import CartItemSerializer


class CartViewSet(viewsets.GenericViewSet):
    """FR-CART-01/03/05: my cart with a fresh server-computed quote per read."""

    def cart(self):
        cart, _ = Cart.objects.get_or_create(user=self.request.user)
        return cart

    def list(self, request):
        cart = self.cart()
        cart.items.exclude(item__available=True).delete()  # FR-CART-02: self-heal stale lines
        coupon, coupon_error = None, None
        if code := request.GET.get("coupon"):
            found = get_coupon(code)
            if found:
                try:
                    coupon = promo.check(found, user=request.user, subtotal_minor=sum(cart.items.values_list("line_total_minor", flat=True)))
                except DomainError as exc:
                    coupon_error = {"code": exc.code, "detail": exc.detail}
        data = quote(
            lines=cart.items.values("line_total_minor"), coupon=coupon,
            delivery_fee_minor=RuntimeConfig.get("delivery.fee_minor", 5000),
            vat_bp=RuntimeConfig.get("pricing.vat_bp", 500),
        )
        data.update({
            "branch": str(cart.branch.uuid) if cart.branch else None,
            "items": CartItemSerializer(cart.items.select_related("item"), many=True).data,
            "meets_minimum": bool(cart.branch and data["items_total_minor"] >= cart.branch.min_order_minor),
        })
        if coupon_error:
            data["coupon_error"] = coupon_error
        return Response(data)

    @action(detail=False, methods=["post"])
    def clear(self, request):
        self.cart().clear()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CartItemViewSet(viewsets.ModelViewSet):
    """Cart line CRUD; option groups validated on every write (FR-CART-02)."""

    serializer_class = CartItemSerializer

    def get_queryset(self):
        return CartItem.objects.filter(cart__user=self.request.user).select_related("item")

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        item = Item.objects.select_related("branch").filter(uuid=request.data.get("item")).first()
        if not item or not item.available:
            raise DomainError("cart.item_unavailable", "This item is not available.")
        cart = Cart.objects.get_or_create(user=request.user)[0]
        if cart.branch and cart.branch_id != item.branch_id and not request.data.get("replace"):
            raise DomainError("cart.branch_conflict", "Cart holds items from another restaurant. Re-send with replace=true.", status.HTTP_409_CONFLICT)
        if request.data.get("replace") or not cart.branch:
            cart.clear()
        cart.branch = item.branch
        cart.save(update_fields=["branch"])
        selected = request.data.get("selected_options", [])
        try:
            qty = max(1, min(int(request.data.get("qty", 1)), 50))
        except (TypeError, ValueError):
            raise DomainError("cart.qty_invalid", "qty must be an integer between 1 and 50.")
        enriched = [{"group_id": s["group_id"], "option_id": s["option_id"], **services.resolve_option(item, s)}
                    for s in selected]
        services.check_group_rules(item, selected)  # FR-CAT-04 min/max rules
        line = CartItem.objects.create(cart=cart, item=item, qty=qty, selected_options=enriched)
        return Response(CartItemSerializer(line).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, pk=None):
        line = self.get_object()
        if (qty := request.data.get("qty")) is not None:
            try:
                line.qty = max(1, min(int(qty), 50))
            except (TypeError, ValueError):
                raise DomainError("cart.qty_invalid", "qty must be an integer between 1 and 50.")
            line.save()
        return Response(CartItemSerializer(line).data)
