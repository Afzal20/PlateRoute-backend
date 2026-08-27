import hashlib
from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from common.errors import DomainError
from common.geo import provider

from .models import MAX_ADDRESSES, Address, GeocodeCache


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = ("uuid", "label", "receiver_name", "phone", "lat", "lng", "plus_code",
                  "street", "area", "city", "postcode", "directions", "is_default", "created_at")


class AddressViewSet(viewsets.ModelViewSet):
    """FR-AUTH-08: the customer address book (max 20 entries)."""

    serializer_class = AddressSerializer
    lookup_field = "uuid"

    def get_queryset(self):
        return self.request.user.addresses.all()

    def perform_create(self, serializer):
        if self.request.user.addresses.count() >= MAX_ADDRESSES:
            raise DomainError("address.limit", f"At most {MAX_ADDRESSES} addresses are allowed.")
        serializer.save(user=self.request.user)

    @action(detail=True, methods=["post"])
    def default(self, request, uuid=None):
        address = self.get_object()
        address.is_default = True
        address.save()
        return Response(self.get_serializer(address).data)


class GeocodeView(APIView):
    """Cache-first autocomplete/reverse proxy over the GeoProvider port (§9)."""

    def get(self, request):
        p = provider()
        if request.GET.get("q"):
            normalized, result = request.GET["q"].strip().lower(), None
        elif request.GET.get("lat") and request.GET.get("lng"):
            normalized = f"rev:{round(float(request.GET['lat']), 5)},{round(float(request.GET['lng']), 5)}"
        else:
            raise DomainError("address.geocode_input", "Provide ?q= or ?lat=&lng=.")
        digest = hashlib.sha256(normalized.encode()).hexdigest()
        row = GeocodeCache.objects.filter(provider=type(p).__name__, input_hash=digest).first()
        if row and row.ttl_expires_at > timezone.now():
            result = row.result
        else:
            result = p.reverse(*(float(request.GET[k]) for k in ("lat", "lng"))) if normalized.startswith("rev:") else p.forward(normalized)
            row, _ = GeocodeCache.objects.update_or_create(
                provider=type(p).__name__, input_hash=digest,
                defaults={"result": result, "ttl_expires_at": timezone.now() + timedelta(days=30)},
            )
        return Response({"input": normalized, "results": result})
