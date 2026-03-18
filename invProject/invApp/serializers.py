from rest_framework import serializers

from .models import Category, Product


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "created_at"]


class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    is_low_stock = serializers.BooleanField(read_only=True)

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
