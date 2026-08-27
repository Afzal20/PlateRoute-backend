from django.core.cache import cache
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import permissions, viewsets
from rest_framework.response import Response

from common.geo import haversine_m
from menus.models import Category
from vendors.models import Branch, Vendor

CACHE_TTL = 60  # §12 performance budget: catalog reads cached 60s


class RestaurantViewSet(viewsets.ViewSet):
    """FR-CAT-05: approved-branch discovery. Read models only (§4 #5)."""

    permission_classes = (permissions.AllowAny,)

    def _visible(self):
        return Branch.objects.filter(vendor__status=Vendor.Status.APPROVED, is_accepting=True).select_related("vendor")

    @staticmethod
    def _row(branch, distance_m=None):
        row = {
            "uuid": str(branch.uuid), "name": branch.name, "vendor": branch.vendor.name,
            "slug": branch.vendor.slug, "cuisines": branch.vendor.cuisines,
            "lat": float(branch.lat), "lng": float(branch.lng), "city": branch.city,
            "min_order_minor": branch.min_order_minor, "prep_minutes": branch.prep_minutes,
            "currency": branch.currency, "rating": float(branch.avg_rating),
            "rating_count": branch.rating_count, "open_now": branch.open_now,
        }
        if distance_m is not None:
            row["distance_m"] = distance_m
        return row

    def list(self, request):
        key = f"discovery:{request.GET.urlencode()}"
        if (rows := cache.get(key)) is not None:
            return Response(rows)
        qs = self._visible()
        if q := request.GET.get("q"):
            branches = list(qs.filter(Q(name__icontains=q) | Q(vendor__name__icontains=q)))
            rows = [self._row(b) for b in branches if q.lower() in str(b.vendor.cuisines).lower()
                    or q.lower() in b.name.lower() or q.lower() in b.vendor.name.lower()]
        else:
            rows = [self._row(b) for b in qs]
        if request.GET.get("open_now"):
            rows = [r for r in rows if r["open_now"]]
        if request.GET.get("lat") and request.GET.get("lng"):
            here = (float(request.GET["lat"]), float(request.GET["lng"]))
            rows.sort(key=lambda r: r.setdefault("distance_m", haversine_m(here, (r["lat"], r["lng"]))))
        cache.set(key, rows, CACHE_TTL)
        return Response(rows)

    def retrieve(self, request, pk=None):
        branch = get_object_or_404(self._visible(), uuid=pk)
        key = f"discovery:menu:{branch.uuid}"
        menu = cache.get(key)
        if menu is None:
            menu = [
                {
                    "name": category.name,
                    "items": [
                        {
                            "uuid": str(item.uuid), "name": item.name, "description": item.description,
                            "image_url": item.image_url, "base_price_minor": item.base_price_minor,
                            "currency": item.currency,
                            "groups": [
                                {
                                    "id": group.id, "title": group.title,
                                    "min_select": group.min_select, "max_select": group.max_select,
                                    "options": [
                                        {"id": option.id, "label": option.label,
                                         "price_delta_minor": option.price_delta_minor,
                                         "is_default": option.is_default}
                                        for option in group.options.filter(available=True)
                                    ],
                                }
                                for group in item.groups.all()
                            ],
                        }
                        for item in category.items.filter(available=True)
                    ],
                }
                for category in branch.categories.all()
            ]
            cache.set(key, menu, CACHE_TTL)
        return Response({**self._row(branch), "menu": menu})
