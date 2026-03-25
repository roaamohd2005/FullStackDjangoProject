from django.urls import path
from rest_framework.routers import DefaultRouter

from . import api_views, auth_views, views

router = DefaultRouter()
router.register("products", api_views.ProductViewSet, basename="api-products")
router.register("categories", api_views.CategoryViewSet, basename="api-categories")

urlpatterns = [
    # Auth routes
    path("register/", auth_views.register, name="register"),
    path("login/", auth_views.user_login, name="login"),
    path("logout/", auth_views.user_logout, name="logout"),
    # App routes
    path("", views.dashboard, name="dashboard"),
    path("categories/add/", views.category_create, name="category_create"),
    path("products/add/", views.product_create, name="product_create"),
    path("products/<int:product_id>/edit/", views.product_edit, name="product_edit"),
    path(
        "products/<int:product_id>/delete/", views.product_delete, name="product_delete"
    ),
    path("products/export/csv/", views.export_products_csv, name="export_products_csv"),
    path("products/export/pdf/", views.export_products_pdf, name="export_products_pdf"),
    path("api/stock-chart/", views.stock_chart_data, name="stock_chart_data"),
]

urlpatterns += router.urls
