from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from common.errors import DomainError
from vendors.models import Branch

from . import services


class BranchReportView(APIView):
    """FR-REP-02: merchant-facing sales summary from nightly aggregates."""

    def get(self, request, branch_uuid):
        branch = get_object_or_404(Branch, uuid=branch_uuid)
        if not branch.is_managed_by(request.user) and not (request.user.is_staff or request.user.role == "operator"):
            raise DomainError("report.forbidden", "Not your branch.", status.HTTP_403_FORBIDDEN)
        return Response(services.branch_summary(branch, days=int(request.GET.get("days", 30))))