from rest_framework import serializers

from .models import Branch, BranchHours, Vendor, VendorStaff


class VendorSerializer(serializers.ModelSerializer):
    slug = serializers.SlugField(required=False)  # generated in create() when absent
    class Meta:
        model = Vendor
        fields = ("slug", "name", "legal_name", "trade_license_no", "cuisines", "status", "commission_bp")
        read_only_fields = ("status",)

    def create(self, validated):
        if not validated.get("slug"):
            from uuid import uuid4
            from django.utils.text import slugify

            validated["slug"] = f"{slugify(validated['name'])}-{uuid4().hex[:6]}"
        validated["owner"] = self.context["request"].user
        return super().create(validated)


class BranchHoursSerializer(serializers.ModelSerializer):
    class Meta:
        model = BranchHours
        fields = ("weekday", "opens", "closes")


class BranchSerializer(serializers.ModelSerializer):
    open_now = serializers.BooleanField(read_only=True)
    vendor_name = serializers.CharField(source="vendor.name", read_only=True)

    class Meta:
        model = Branch
        fields = ("uuid", "vendor", "vendor_name", "name", "lat", "lng", "address_text", "city", "phone",
                  "prep_minutes", "min_order_minor", "currency", "open_hours", "open_now",
                  "avg_rating", "rating_count", "is_accepting")
        read_only_fields = ("uuid", "vendor", "vendor_name")

    def create(self, validated):
        branch = Branch.objects.create(vendor=self.context["vendor"], **validated)
        if branch.vendor.status == Vendor.Status.DRAFT:
            branch.vendor.status = Vendor.Status.PENDING
            branch.vendor.save(update_fields=["status"])
        return branch


class StaffSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = VendorStaff
        fields = ("id", "branch", "user", "email", "role")
        read_only_fields = ("id", "branch")

    def validate_user(self, user):
        if user.role != "vendor":
            raise serializers.ValidationError("User must have the vendor role.")
        return user
