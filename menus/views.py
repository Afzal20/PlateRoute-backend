from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from common.errors import DomainError
from common.permissions import role_required
from vendors.models import Branch

from .models import Category, Item
from .serializers import CategorySerializer, ItemSerializer


class MenuViewSet(viewsets.ModelViewSet):
    """Shared scoping for menu write surfaces: vendor-role + branch staff."""

    permission_classes = (role_required("vendor"),)
    lookup_field = "uuid"

    def _managed_branch(self, branch_uuid):
        branch = Branch.objects.filter(uuid=branch_uuid).first()
        if not branch or not branch.is_managed_by(self.request.user):
            raise DomainError("branch.forbidden", "Branch not found or not yours.")
        return branch


class CategoryViewSet(MenuViewSet):
    serializer_class = CategorySerializer

    def get_queryset(self):
        qs = Category.objects.filter(branch__vendor__owner=self.request.user) | \
             Category.objects.filter(branch__staff__user=self.request.user)
        if branch := self.request.GET.get("branch"):
            qs = qs.filter(branch__uuid=branch)
        return qs

    def perform_create(self, serializer):
        if not serializer.validated_data["branch"].is_managed_by(self.request.user):
            raise DomainError("branch.forbidden", "Branch not found or not yours.")
        serializer.save()


class ItemViewSet(MenuViewSet):
    serializer_class = ItemSerializer

    def get_queryset(self):
        qs = Item.objects.filter(branch__vendor__owner=self.request.user) | \
             Item.objects.filter(branch__staff__user=self.request.user)
        if branch := self.request.GET.get("branch"):
            qs = qs.filter(branch__uuid=branch)
        return qs.select_related("category")

    def perform_create(self, serializer):
        category = serializer.validated_data["category"]
        self._managed_branch(str(category.branch.uuid))
        serializer.save()

    @action(detail=True, methods=["post"])
    def toggle(self, request, uuid=None):
        """FR-CAT-03 availability switch, reflected immediately in discovery."""
        item = self.get_object()
        item.available = not item.available
        item.save(update_fields=["available", "branch_id"])
        return Response(ItemSerializer(item).data)
