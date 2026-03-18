from django import forms
from .models import Category, Product


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name"]
        widgets = {
            "name": forms.TextInput(
                attrs={"placeholder": "e.g. Electronics", "class": "form-control"}
            )
        }


class ProductForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        owner = kwargs.pop("owner", None)
        super().__init__(*args, **kwargs)
        if owner is not None:
            self.fields["category"].queryset = Category.objects.filter(owner=owner)

    class Meta:
        model = Product
        fields = ["name", "category", "sku", "price", "quantity", "supplier"]
        widgets = {
            "name": forms.TextInput(
                attrs={"placeholder": "e.g. Cotton Shirt", "class": "form-control"}
            ),
            "category": forms.Select(attrs={"class": "form-control"}),
            "sku": forms.TextInput(
                attrs={"placeholder": "e.g. SKU-1001", "class": "form-control"}
            ),
            "price": forms.NumberInput(
                attrs={"placeholder": "e.g. 19.99", "step": "0.01", "class": "form-control"}
            ),
            "quantity": forms.NumberInput(
                attrs={"placeholder": "e.g. 80", "class": "form-control"}
            ),
            "supplier": forms.TextInput(
                attrs={"placeholder": "e.g. ABC Corp", "class": "form-control"}
            ),
        }

    def clean_price(self):
        price = self.cleaned_data["price"]
        if price <= 0:
            raise forms.ValidationError("Price must be greater than 0.")
        return price

    def clean_quantity(self):
        quantity = self.cleaned_data["quantity"]
        if quantity < 0:
            raise forms.ValidationError("Quantity cannot be negative.")
        return quantity