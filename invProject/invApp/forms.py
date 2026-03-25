from django import forms

from .models import Category, Product


class CategoryForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.owner = kwargs.pop("owner", None)
        super().__init__(*args, **kwargs)

    class Meta:
        model = Category
        fields = ["name"]
        widgets = {
            "name": forms.TextInput(
                attrs={"placeholder": "e.g. Electronics", "class": "form-control"}
            )
        }

    def clean_name(self):
        name = self.cleaned_data.get("name")
        if not name or not self.owner:
            return name

        if Category.objects.filter(owner=self.owner, name__iexact=name).exists():
            raise forms.ValidationError("You already have a category with this name.")

        return name.strip()


class ProductForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.owner = kwargs.pop("owner", None)
        super().__init__(*args, **kwargs)

        # Always start with empty queryset for security
        self.fields["category"].queryset = Category.objects.none()
        self.fields["category"].required = False

        if self.owner is not None:
            self.fields["category"].queryset = Category.objects.filter(owner=self.owner)

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
                attrs={
                    "placeholder": "e.g. 19.99",
                    "step": "0.01",
                    "class": "form-control",
                }
            ),
            "quantity": forms.NumberInput(
                attrs={"placeholder": "e.g. 80", "class": "form-control"}
            ),
            "supplier": forms.TextInput(
                attrs={"placeholder": "e.g. ABC Corp", "class": "form-control"}
            ),
        }

    def clean_price(self):
        price = self.cleaned_data.get("price")
        if price is not None and price <= 0:
            raise forms.ValidationError("Price must be greater than 0.")
        return price

    def clean_quantity(self):
        quantity = self.cleaned_data.get("quantity")
        if quantity is not None and quantity < 0:
            raise forms.ValidationError("Quantity cannot be negative.")
        return quantity

    def clean_sku(self):
        sku = self.cleaned_data.get("sku")
        if not sku or not self.owner:
            return sku

        duplicate_qs = Product.objects.filter(owner=self.owner, sku__iexact=sku.strip())

        if self.instance and self.instance.pk:
            duplicate_qs = duplicate_qs.exclude(pk=self.instance.pk)

        if duplicate_qs.exists():
            raise forms.ValidationError("You already have a product with this SKU.")

        return sku.strip()

    def clean_category(self):
        category = self.cleaned_data.get("category")
        if category and self.owner and category.owner_id != self.owner.id:
            raise forms.ValidationError(
                "Selected category does not belong to your account."
            )

        return category
