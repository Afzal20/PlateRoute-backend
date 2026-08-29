from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from common.errors import DomainError
from orders.models import Order

from .models import Review, ReviewReply


class ReviewCreateView(APIView):
    """FR-RVW-01: a customer reviews their own, already-delivered order once."""

    def post(self, request):
        order = get_object_or_404(Order.objects.select_related("branch"), uuid=request.data.get("order", ""))
        if order.customer_id != request.user.id:
            raise DomainError("review.forbidden", "You can only review your own orders.", status.HTTP_403_FORBIDDEN)
        if order.status != Order.Status.DELIVERED:
            raise DomainError("review.not_delivered", "Only delivered orders can be reviewed.", status.HTTP_409_CONFLICT)
        if hasattr(order, "review"):
            raise DomainError("review.already_exists", "This order is already reviewed.", status.HTTP_409_CONFLICT)
        body = (request.data.get("body") or "").strip()
        review = Review.objects.create(order=order,
                                       restaurant_stars=int(request.data.get("restaurant_stars") or 5),
                                       courier_stars=request.data.get("courier_stars"),
                                       body=body[:1000] if isinstance(body, str) else body)
        return Response(self._serialize(review), status=status.HTTP_201_CREATED)

    @staticmethod
    def _serialize(review):
        return {"order": str(review.order.uuid), "restaurant_stars": review.restaurant_stars,
                "courier_stars": review.courier_stars, "body": review.body, "id": review.id}


class ReviewListView(APIView):
    """Public reviews for a branch (visible ones only)."""

    permission_classes = ()

    def get(self, request, branch_uuid):
        from vendors.models import Branch
        branch = get_object_or_404(Branch, uuid=branch_uuid)
        reviews = Review.objects.filter(order__branch=branch, hidden_at__isnull=True) \
            .select_related("order", "order__customer").order_by("-created_at")[:50]
        return Response([
            {"id": r.id, "restaurant_stars": r.restaurant_stars, "courier_stars": r.courier_stars,
             "body": r.body, "customer": r.order.customer.email, "reply": r.reply.body if hasattr(r, "reply") else None,
             "created_at": r.created_at}
            for r in reviews
        ])


class ReviewReplyView(APIView):
    """FR-RVW-02: the branch (owner or staff) replies on a review."""

    def post(self, request, pk):
        review = get_object_or_404(Review.objects.select_related("order__branch"), pk=pk)
        if not review.order.branch.is_managed_by(request.user):
            raise DomainError("review.forbidden", "Not your restaurant.", status.HTTP_403_FORBIDDEN)
        if hasattr(review, "reply"):
            raise DomainError("review.replied", "This review already has a reply.", status.HTTP_409_CONFLICT)
        reply = ReviewReply.objects.create(review=review, author=request.user, body=(request.data.get("body") or "")[:1000])
        return Response({"id": reply.id, "body": reply.body}, status=status.HTTP_201_CREATED)