from django.db import IntegrityError
from rest_framework import permissions, viewsets
from rest_framework.exceptions import ValidationError

from .models import Category, Product
from .serializers import CategorySerializer, ProductSerializer


class IsOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return getattr(obj, "owner_id", None) == request.user.id


class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated, IsOwner]

    def get_queryset(self):
        return Category.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        try:
            serializer.save(owner=self.request.user)
        except IntegrityError as exc:
            # Defensive fallback: if DB uniqueness is hit after serializer checks,
            # return a clean field-level 400 instead of surfacing a 500.
            raise ValidationError(
                {"name": ["You already have a category with this name."]}
            ) from exc


class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwner]

    def get_queryset(self):
        return Product.objects.filter(owner=self.request.user).select_related(
            "category"
        )

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
