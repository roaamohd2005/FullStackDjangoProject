import csv
from decimal import Decimal
from io import BytesIO
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import DecimalField, ExpressionWrapper, F, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from .forms import CategoryForm, ProductForm
from .models import ActivityLog, Category, Product


def _dashboard_base_queryset(request):
    search = request.GET.get("search", "").strip()
    supplier = request.GET.get("supplier", "").strip()
    category_id = request.GET.get("category", "").strip()
    sort = request.GET.get("sort", "name")

    products = Product.objects.filter(owner=request.user).select_related("category")
    if search:
        products = products.filter(
            Q(name__icontains=search)
            | Q(sku__icontains=search)
            | Q(supplier__icontains=search)
            | Q(category__name__icontains=search)
        )
    if supplier:
        products = products.filter(supplier=supplier)
    if category_id:
        products = products.filter(category_id=category_id)

    sort_map = {
        "name": "name",
        "price": "-price",
        "quantity": "quantity",
        "sku": "sku",
        "updated": "-updated_at",
    }
    products = products.order_by(sort_map.get(sort, "name"))

    return {
        "products": products,
        "search": search,
        "supplier": supplier,
        "category_id": category_id,
        "sort": sort,
    }


def _dashboard_export_query_string(base):
    query = {
        "search": base["search"],
        "supplier": base["supplier"],
        "category": base["category_id"],
        "sort": base["sort"],
    }
    return urlencode(query)


def _build_dashboard_context(
    request,
    *,
    product_form=None,
    category_form=None,
    modal_state="",
    editing_product_id=None,
):
    base = _dashboard_base_queryset(request)
    products = base["products"]

    paginator = Paginator(products, 8)
    page_obj = paginator.get_page(request.GET.get("page"))

    all_products = Product.objects.filter(owner=request.user)
    total_products = all_products.count()
    total_quantity = all_products.aggregate(total=Coalesce(Sum("quantity"), 0))["total"]
    total_value = all_products.aggregate(
        total=Coalesce(
            Sum(
                ExpressionWrapper(
                    F("price") * F("quantity"),
                    output_field=DecimalField(max_digits=14, decimal_places=2),
                )
            ),
            Value(
                Decimal("0.00"),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            ),
        )
    )["total"]
    low_stock_count = all_products.filter(quantity__lte=10).count()

    context = {
        "page_obj": page_obj,
        "products": page_obj.object_list,
        "search": base["search"],
        "supplier": base["supplier"],
        "category_id": base["category_id"],
        "sort": base["sort"],
        "export_query_string": _dashboard_export_query_string(base),
        "suppliers": all_products.values_list("supplier", flat=True)
        .distinct()
        .order_by("supplier"),
        "categories": Category.objects.filter(owner=request.user).order_by("name"),
        "total_products": total_products,
        "total_quantity": total_quantity,
        "total_value": total_value,
        "low_stock_count": low_stock_count,
        "activity_logs": ActivityLog.objects.filter(user=request.user)[:8],
        "product_form": product_form or ProductForm(owner=request.user),
        "category_form": category_form or CategoryForm(owner=request.user),
        "modal_state": modal_state,
        "editing_product_id": editing_product_id,
    }
    return context


@login_required(login_url="login")
def dashboard(request):
    context = _build_dashboard_context(request)
    return render(request, "invApp/dashboard.html", context)


@login_required(login_url="login")
def product_create(request):
    if request.method == "POST":
        form = ProductForm(
            request.POST, owner=request.user, instance=Product(owner=request.user)
        )
        if form.is_valid():
            product = form.save()
            ActivityLog.objects.create(
                user=request.user,
                product=product,
                action=ActivityLog.ACTION_ADDED,
                details=f"Added product {product.name} ({product.sku})",
            )
            messages.success(request, "Product created successfully.")
            return redirect("dashboard")
        else:
            messages.error(
                request, "Could not create product. Fix the highlighted fields."
            )
            context = _build_dashboard_context(
                request,
                product_form=form,
                modal_state="product_create",
            )
            return render(request, "invApp/dashboard.html", context, status=400)
    return redirect("dashboard")


@login_required(login_url="login")
def product_edit(request, product_id):
    product = get_object_or_404(Product, product_id=product_id, owner=request.user)
    if request.method == "POST":
        form = ProductForm(request.POST, instance=product, owner=request.user)
        if form.is_valid():
            product = form.save()
            ActivityLog.objects.create(
                user=request.user,
                product=product,
                action=ActivityLog.ACTION_EDITED,
                details=f"Edited product {product.name} ({product.sku})",
            )
            messages.success(request, "Product updated successfully.")
            return redirect("dashboard")
        else:
            messages.error(
                request, "Could not update product. Fix the highlighted fields."
            )
            context = _build_dashboard_context(
                request,
                product_form=form,
                modal_state="product_edit",
                editing_product_id=product.product_id,
            )
            return render(request, "invApp/dashboard.html", context, status=400)
    return redirect("dashboard")


@login_required(login_url="login")
def product_delete(request, product_id):
    product = get_object_or_404(Product, product_id=product_id, owner=request.user)
    if request.method == "POST":
        name = product.name
        sku = product.sku
        product.delete()
        ActivityLog.objects.create(
            user=request.user,
            action=ActivityLog.ACTION_DELETED,
            details=f"Deleted product {name} ({sku})",
        )
        messages.success(request, "Product deleted successfully.")
    return redirect("dashboard")


@login_required(login_url="login")
def category_create(request):
    if request.method == "POST":
        form = CategoryForm(request.POST, owner=request.user)
        if form.is_valid():
            category = form.save(commit=False)
            category.owner = request.user
            category.save()
            messages.success(request, "Category added.")
            return redirect("dashboard")
        else:
            messages.error(
                request, "Could not create category. Fix the highlighted fields."
            )
            context = _build_dashboard_context(
                request,
                category_form=form,
                modal_state="category",
            )
            return render(request, "invApp/dashboard.html", context, status=400)
    return redirect("dashboard")


@login_required(login_url="login")
def stock_chart_data(request):
    products = Product.objects.filter(owner=request.user).order_by("name")
    labels = [product.name for product in products]
    quantities = [product.quantity for product in products]
    values = [round(product.quantity * product.price, 2) for product in products]

    return JsonResponse({"labels": labels, "quantities": quantities, "values": values})


@login_required(login_url="login")
def export_products_csv(request):
    products = _dashboard_base_queryset(request)["products"]

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = "attachment; filename=products.csv"
    writer = csv.writer(response)
    writer.writerow(
        ["Name", "Category", "SKU", "Price", "Quantity", "Supplier", "Low Stock"]
    )

    for product in products:
        writer.writerow(
            [
                product.name,
                product.category.name if product.category else "",
                product.sku,
                product.price,
                product.quantity,
                product.supplier,
                "Yes" if product.is_low_stock else "No",
            ]
        )
    return response


@login_required(login_url="login")
def export_products_pdf(request):
    products = _dashboard_base_queryset(request)["products"]

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    y = 760
    p.setFont("Helvetica-Bold", 13)
    p.drawString(40, y, f"Inventory Report - {request.user.username}")
    y -= 25
    p.setFont("Helvetica", 10)

    for product in products:
        line = (
            f"{product.name} | {product.sku} | Qty: "
            f"{product.quantity} | ${product.price:.2f}"
        )
        p.drawString(40, y, line)
        y -= 16
        if y < 50:
            p.showPage()
            y = 760
            p.setFont("Helvetica", 10)

    p.save()
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = "attachment; filename=products.pdf"
    return response
