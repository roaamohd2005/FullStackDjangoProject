from rest_framework import serializers

from .models import Category, Product


class CategorySerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.owner = self.context.get("owner")
        if self.owner is None:
            request = self.context.get("request")
            self.owner = getattr(request, "user", None) if request else None

    def validate_name(self, value):
        if not value or not self.owner or not self.owner.is_authenticated:
            return value

        normalized_name = value.strip()
        duplicate_qs = Category.objects.filter(
            owner=self.owner,
            name__iexact=normalized_name,
        )

        if self.instance is not None:
            duplicate_qs = duplicate_qs.exclude(pk=self.instance.pk)

        if duplicate_qs.exists():
            raise serializers.ValidationError(
                "You already have a category with this name."
            )

        return normalized_name

    class Meta:
        model = Category
        fields = ["id", "name", "created_at"]


class ProductSerializer(serializers.ModelSerializer):
    category = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.none(), required=False, allow_null=True
    )
    category_name = serializers.CharField(source="category.name", read_only=True)
    is_low_stock = serializers.BooleanField(read_only=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Explicitly get owner from context (best practice)
        self.owner = self.context.get("owner")

        # Fallback to request.user if owner was not passed explicitly
        if self.owner is None:
            request = self.context.get("request")
            self.owner = getattr(request, "user", None) if request else None

        # Filter category queryset based on owner
        if self.owner and self.owner.is_authenticated:
            self.fields["category"].queryset = Category.objects.filter(owner=self.owner)
        else:
            self.fields["category"].queryset = Category.objects.none()

    def validate_sku(self, value):
        if not value or not self.owner or not self.owner.is_authenticated:
            return value

        duplicate_qs = Product.objects.filter(
            owner=self.owner, sku__iexact=value.strip()
        )

        if self.instance is not None:
            duplicate_qs = duplicate_qs.exclude(pk=self.instance.pk)

        if duplicate_qs.exists():
            raise serializers.ValidationError(
                "You already have a product with this SKU."
            )

        return value.strip()

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Price must be greater than 0.")
        return value

    def validate_category(self, value):
        if value is None or not self.owner or not self.owner.is_authenticated:
            return value

        if value.owner_id != self.owner.id:
            raise serializers.ValidationError(
                "Selected category does not belong to your account."
            )

        return value

    class Meta:
        model = Product
        fields = [
            "product_id",
            "name",
            "category",
            "category_name",
            "sku",
            "price",
            "quantity",
            "supplier",
            "is_low_stock",
            "created_at",
            "updated_at",
        ]
