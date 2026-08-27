from django.db import transaction
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from common.permissions import role_required

from .models import Branch, BranchHours, Vendor, VendorStaff
from .serializers import BranchHoursSerializer, BranchSerializer, StaffSerializer, VendorSerializer


class VendorViewSet(viewsets.ModelViewSet):
    """FR-CAT-01/02: vendor onboarding; submit moves draft -> pending review."""

    serializer_class = VendorSerializer
    lookup_field = "slug"
    permission_classes = (role_required("vendor"),)

    def get_queryset(self):
        return Vendor.objects.filter(owner=self.request.user)

    @action(detail=True, methods=["post"])
    def submit(self, request, slug=None):
        vendor = self.get_object()
        if vendor.status != Vendor.Status.DRAFT:
            return Response({"detail": "Only draft vendors can be submitted."}, status=409)
        vendor.status = Vendor.Status.PENDING
        vendor.save(update_fields=["status"])
        return Response(VendorSerializer(vendor).data)


class BranchViewSet(viewsets.ModelViewSet):
    """Branch CRUD scoped to the vendor owner or invited branch staff."""

    serializer_class = BranchSerializer
    lookup_field = "uuid"

    def get_queryset(self):
        user = self.request.user
        return Branch.objects.filter(vendor__owner=user) | Branch.objects.filter(staff__user=user)

    def get_permissions(self):
        return [role_required("vendor")()] if self.request.method != "GET" else [permissions.IsAuthenticated()]

    def get_serializer_context(self):
        return {**super().get_serializer_context(), "vendor": self._vendor()}

    def _vendor(self):
        ref = self.kwargs.get("vendor_uuid") or self.request.data.get("vendor")
        return Vendor.objects.filter(slug=ref).first()

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def hours(self, request, uuid=None):
        """Bulk-replace the weekly opening-hours matrix."""
        branch = self.get_object()
        serializer = BranchHoursSerializer(data=request.data.get("hours", []), many=True)
        serializer.is_valid(raise_exception=True)
        branch.hours.all().delete()
        BranchHours.objects.bulk_create(BranchHours(branch=branch, **row) for row in serializer.validated_data)
        return Response(serializer.data, status=201)

    @action(detail=True, methods=["get", "post"])
    def team(self, request, uuid=None):
        """List or invite branch staff members (FR-CAT-01)."""
        branch = self.get_object()
        if request.method == "GET":
            return Response(StaffSerializer(branch.staff.all(), many=True).data)
        serializer = StaffSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(branch=branch, invited_by=request.user)
        return Response(serializer.data, status=201)
