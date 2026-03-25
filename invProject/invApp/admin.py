from django.contrib import admin

from .models import ActivityLog, Category, Product


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "owner", "created_at")
    search_fields = ("name", "owner__username")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "product_id",
        "name",
        "owner",
        "category",
        "sku",
        "price",
        "quantity",
        "supplier",
    )
    search_fields = ("name", "sku", "supplier", "owner__username")
    list_filter = ("supplier", "category")


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "action", "details", "created_at")
    search_fields = ("user__username", "details")
    list_filter = ("action",)
