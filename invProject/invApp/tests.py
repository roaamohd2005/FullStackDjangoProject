from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from .models import ActivityLog, Category, Product

User = get_user_model()


class AuthViewsTests(TestCase):
    def test_register_page_loads(self):
        response = self.client.get(reverse("register"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Create Account")

    def test_user_registration(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "testuser",
                "email": "test@example.com",
                "password1": "securepass123",
                "password2": "securepass123",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(username="testuser").exists())

    def test_registration_enforces_password_policy(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "weakpassuser",
                "email": "weakpass@example.com",
                "password1": "password",
                "password2": "password",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="weakpassuser").exists())
        self.assertContains(response, "This password is too common.")

    def test_registration_rejects_six_character_password(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "shortpassuser",
                "email": "shortpass@example.com",
                "password1": "abc123",
                "password2": "abc123",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="shortpassuser").exists())
        self.assertContains(response, "This password is too short")

    def test_login_page_loads(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sign In")

    def test_user_login(self):
        User.objects.create_user(username="testuser", password="testpass123")
        response = self.client.post(
            reverse("login"),
            {"username": "testuser", "password": "testpass123"},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_register_then_logout_then_login(self):
        register_response = self.client.post(
            reverse("register"),
            {
                "username": "newuser",
                "email": "newuser@example.com",
                "password1": "securepass123",
                "password2": "securepass123",
            },
            follow=True,
        )
        self.assertEqual(register_response.status_code, 200)
        self.assertTrue(register_response.wsgi_request.user.is_authenticated)

        logout_response = self.client.post(reverse("logout"), follow=True)
        self.assertEqual(logout_response.status_code, 200)
        self.assertFalse(logout_response.wsgi_request.user.is_authenticated)

        login_response = self.client.post(
            reverse("login"),
            {"username": "newuser", "password": "securepass123"},
            follow=True,
        )
        self.assertEqual(login_response.status_code, 200)
        self.assertTrue(login_response.wsgi_request.user.is_authenticated)

    def test_user_can_login_with_email(self):
        User.objects.create_user(
            username="emailuser",
            email="emailuser@example.com",
            password="testpass123",
        )
        response = self.client.post(
            reverse("login"),
            {"username": "emailuser@example.com", "password": "testpass123"},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_logout_get_is_rejected(self):
        user = User.objects.create_user(username="logout_user", password="testpass123")
        self.client.force_login(user)

        response = self.client.get(reverse("logout"), follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.wsgi_request.user.is_authenticated)


class InventoryViewsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.other_user = User.objects.create_user(
            username="otheruser", password="testpass123"
        )
        self.category = Category.objects.create(owner=self.user, name="Apparel")
        self.other_category = Category.objects.create(
            owner=self.other_user, name="Hardware"
        )
        self.tools_category = Category.objects.create(owner=self.user, name="Tools")
        self.product = Product.objects.create(
            owner=self.user,
            category=self.category,
            name="Cotton Shirt",
            sku="SKU-1001",
            price=Decimal("24.99"),
            quantity=50,
            supplier="ABC Corp",
        )
        self.other_product = Product.objects.create(
            owner=self.other_user,
            category=self.other_category,
            name="Hammer",
            sku="SKU-2001",
            price=Decimal("12.00"),
            quantity=15,
            supplier="ToolCo",
        )

    def test_dashboard_redirects_unauthenticated(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/login/"))

    def test_dashboard_renders_authenticated(self):
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Inventory Plus")

    def test_dashboard_filters_with_search_supplier_category_combination(self):
        self.client.login(username="testuser", password="testpass123")
        target = Product.objects.create(
            owner=self.user,
            category=self.tools_category,
            name="Blue Drill",
            sku="TOOL-100",
            price=Decimal("90.00"),
            quantity=4,
            supplier="Acme Tools",
        )
        Product.objects.create(
            owner=self.user,
            category=self.tools_category,
            name="Blue Saw",
            sku="TOOL-101",
            price=Decimal("50.00"),
            quantity=10,
            supplier="Acme Tools",
        )
        Product.objects.create(
            owner=self.user,
            category=self.category,
            name="Blue Drill Copy",
            sku="APP-100",
            price=Decimal("40.00"),
            quantity=9,
            supplier="Acme Tools",
        )

        response = self.client.get(
            reverse("dashboard"),
            {
                "search": "drill",
                "supplier": "Acme Tools",
                "category": str(self.tools_category.id),
                "sort": "name",
            },
        )

        self.assertEqual(response.status_code, 200)
        products = list(response.context["products"])
        self.assertEqual(products, [target])
        self.assertEqual(response.context["page_obj"].paginator.count, 1)

    def test_dashboard_search_matches_sku_supplier_and_category_name(self):
        self.client.login(username="testuser", password="testpass123")
        sku_match = Product.objects.create(
            owner=self.user,
            category=self.tools_category,
            name="Cordless Driver",
            sku="MATCH-SKU-001",
            price=Decimal("80.00"),
            quantity=5,
            supplier="ProSupply",
        )
        supplier_match = Product.objects.create(
            owner=self.user,
            category=self.category,
            name="Safety Gloves",
            sku="SAFE-001",
            price=Decimal("12.00"),
            quantity=20,
            supplier="Match Supplier",
        )

        sku_response = self.client.get(reverse("dashboard"), {"search": "match-sku"})
        self.assertEqual(sku_response.status_code, 200)
        self.assertIn(sku_match, list(sku_response.context["products"]))

        supplier_response = self.client.get(
            reverse("dashboard"), {"search": "match supplier"}
        )
        self.assertEqual(supplier_response.status_code, 200)
        self.assertIn(supplier_match, list(supplier_response.context["products"]))

        category_response = self.client.get(reverse("dashboard"), {"search": "tools"})
        self.assertEqual(category_response.status_code, 200)
        self.assertIn(sku_match, list(category_response.context["products"]))

    def test_dashboard_sorting_by_price_and_quantity(self):
        self.client.login(username="testuser", password="testpass123")
        expensive = Product.objects.create(
            owner=self.user,
            category=self.tools_category,
            name="Laser Cutter",
            sku="TOOL-200",
            price=Decimal("199.99"),
            quantity=8,
            supplier="Acme Tools",
        )
        minimal_qty = Product.objects.create(
            owner=self.user,
            category=self.tools_category,
            name="Fine Brush",
            sku="TOOL-201",
            price=Decimal("5.00"),
            quantity=0,
            supplier="Acme Tools",
        )

        price_response = self.client.get(reverse("dashboard"), {"sort": "price"})
        self.assertEqual(price_response.status_code, 200)
        price_sorted = list(price_response.context["products"])
        self.assertEqual(price_sorted[0], expensive)

        quantity_response = self.client.get(reverse("dashboard"), {"sort": "quantity"})
        self.assertEqual(quantity_response.status_code, 200)
        quantity_sorted = list(quantity_response.context["products"])
        self.assertEqual(quantity_sorted[0], minimal_qty)

    def test_dashboard_sorting_by_updated_shows_recently_updated_first(self):
        self.client.login(username="testuser", password="testpass123")
        older = Product.objects.create(
            owner=self.user,
            category=self.tools_category,
            name="Old Item",
            sku="OLD-001",
            price=Decimal("15.00"),
            quantity=3,
            supplier="Acme Tools",
        )
        newer = Product.objects.create(
            owner=self.user,
            category=self.tools_category,
            name="New Item",
            sku="NEW-001",
            price=Decimal("25.00"),
            quantity=4,
            supplier="Acme Tools",
        )
        older.name = "Old Item Updated"
        older.save()

        response = self.client.get(reverse("dashboard"), {"sort": "updated"})

        self.assertEqual(response.status_code, 200)
        updated_sorted = list(response.context["products"])
        self.assertEqual(updated_sorted[0], older)
        self.assertIn(newer, updated_sorted)

    def test_dashboard_pagination_preserves_active_filters(self):
        self.client.login(username="testuser", password="testpass123")
        for idx in range(1, 10):
            Product.objects.create(
                owner=self.user,
                category=self.tools_category,
                name=f"Pager Item {idx:02d}",
                sku=f"PG-{idx:03d}",
                price=Decimal("10.00") + Decimal(str(idx)),
                quantity=idx,
                supplier="PagerCo",
            )

        response = self.client.get(
            reverse("dashboard"),
            {
                "supplier": "PagerCo",
                "sort": "name",
                "page": 2,
            },
        )

        self.assertEqual(response.status_code, 200)
        page_obj = response.context["page_obj"]
        products = list(response.context["products"])
        self.assertEqual(page_obj.number, 2)
        self.assertEqual(page_obj.paginator.count, 9)
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0].name, "Pager Item 09")
        self.assertContains(
            response,
            "?page=1&search=&supplier=PagerCo&category=&sort=name",
        )

    def test_dashboard_invalid_page_number_falls_back_to_last_page(self):
        self.client.login(username="testuser", password="testpass123")
        for idx in range(1, 12):
            Product.objects.create(
                owner=self.user,
                category=self.tools_category,
                name=f"Page Item {idx:02d}",
                sku=f"PGX-{idx:03d}",
                price=Decimal("11.00") + Decimal(str(idx)),
                quantity=idx,
                supplier="PagerCo",
            )

        response = self.client.get(reverse("dashboard"), {"page": "999"})

        self.assertEqual(response.status_code, 200)
        page_obj = response.context["page_obj"]
        self.assertEqual(page_obj.number, page_obj.paginator.num_pages)
        self.assertTrue(page_obj.has_previous())

    def test_create_product_authenticated(self):
        self.client.login(username="testuser", password="testpass123")
        response = self.client.post(
            reverse("product_create"),
            {
                "name": "Sneakers",
                "category": self.category.id,
                "sku": "SKU-1002",
                "price": 59.9,
                "quantity": 20,
                "supplier": "RunFast",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Product.objects.filter(sku="SKU-1002").exists())

    def test_duplicate_sku_shows_field_error(self):
        self.client.login(username="testuser", password="testpass123")

        response = self.client.post(
            reverse("product_create"),
            {
                "name": "Cotton Shirt Duplicate",
                "category": self.category.id,
                "sku": "SKU-1001",
                "price": "10.00",
                "quantity": 5,
                "supplier": "ABC Corp",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            "You already have a product with this SKU.",
            status_code=400,
        )

    def test_edit_other_users_product_forbidden(self):
        self.client.login(username="testuser", password="testpass123")
        response = self.client.post(
            reverse("product_edit", args=[self.other_product.product_id]),
            {
                "name": "Changed",
                "category": self.other_category.id,
                "sku": "SKU-2001",
                "price": "10.00",
                "quantity": 5,
                "supplier": "X",
            },
        )

        self.assertEqual(response.status_code, 404)

    def test_delete_other_users_product_forbidden(self):
        self.client.login(username="testuser", password="testpass123")
        response = self.client.post(
            reverse("product_delete", args=[self.other_product.product_id])
        )
        self.assertEqual(response.status_code, 404)

    def test_create_product_with_other_users_category_rejected(self):
        self.client.login(username="testuser", password="testpass123")
        response = self.client.post(
            reverse("product_create"),
            {
                "name": "Sneakers",
                "category": self.other_category.id,
                "sku": "SKU-1009",
                "price": "59.90",
                "quantity": 20,
                "supplier": "RunFast",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Select a valid choice", status_code=400)

    def test_chart_api_authenticated(self):
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("stock_chart_data"))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("labels", payload)
        self.assertIn("quantities", payload)

    def test_chart_api_returns_empty_arrays_when_user_has_no_products(self):
        self.client.login(username="testuser", password="testpass123")
        Product.objects.filter(owner=self.user).delete()

        response = self.client.get(reverse("stock_chart_data"))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["labels"], [])
        self.assertEqual(payload["quantities"], [])
        self.assertEqual(payload["values"], [])

    def test_dashboard_contains_chart_empty_state_markup(self):
        self.client.login(username="testuser", password="testpass123")

        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="chartEmptyState"')
        self.assertContains(response, "No stock data yet")

    def test_invalid_price_shows_field_error(self):
        self.client.login(username="testuser", password="testpass123")
        response = self.client.post(
            reverse("product_create"),
            {
                "name": "Bad Price Item",
                "category": self.category.id,
                "sku": "SKU-3001",
                "price": "0",
                "quantity": 3,
                "supplier": "SupplierX",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Price must be greater than 0.", status_code=400)

    def test_invalid_quantity_shows_field_error(self):
        self.client.login(username="testuser", password="testpass123")
        response = self.client.post(
            reverse("product_create"),
            {
                "name": "Bad Qty Item",
                "category": self.category.id,
                "sku": "SKU-3002",
                "price": "12.50",
                "quantity": -1,
                "supplier": "SupplierX",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "greater than or equal to 0", status_code=400)

    def test_duplicate_category_name_shows_field_error(self):
        self.client.login(username="testuser", password="testpass123")
        response = self.client.post(
            reverse("category_create"),
            {"name": "apparel"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            "You already have a category with this name.",
            status_code=400,
        )

    def test_get_product_delete_does_not_delete(self):
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(
            reverse("product_delete", args=[self.product.product_id])
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Product.objects.filter(product_id=self.product.product_id).exists()
        )

    def test_export_csv_requires_authentication(self):
        response = self.client.get(reverse("export_products_csv"))

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/login/"))

    def test_export_csv_contains_only_owned_products(self):
        self.client.login(username="testuser", password="testpass123")

        response = self.client.get(reverse("export_products_csv"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn(
            "attachment; filename=products.csv", response["Content-Disposition"]
        )

        csv_text = response.content.decode("utf-8")
        self.assertIn("Name,Category,SKU,Price,Quantity,Supplier,Low Stock", csv_text)
        self.assertIn("Cotton Shirt,Apparel,SKU-1001,24.99,50,ABC Corp,No", csv_text)
        self.assertNotIn("Hammer", csv_text)
        self.assertNotIn("SKU-2001", csv_text)

    def test_export_csv_mirrors_active_filters(self):
        self.client.login(username="testuser", password="testpass123")
        Product.objects.create(
            owner=self.user,
            category=self.tools_category,
            name="Filter Match",
            sku="FLT-100",
            price=Decimal("30.00"),
            quantity=2,
            supplier="PagerCo",
        )
        Product.objects.create(
            owner=self.user,
            category=self.tools_category,
            name="Filter Miss",
            sku="FLT-101",
            price=Decimal("40.00"),
            quantity=3,
            supplier="OtherCo",
        )

        response = self.client.get(
            reverse("export_products_csv"),
            {"supplier": "PagerCo", "sort": "name"},
        )

        self.assertEqual(response.status_code, 200)
        csv_text = response.content.decode("utf-8")
        self.assertIn("Filter Match", csv_text)
        self.assertNotIn("Filter Miss", csv_text)
        self.assertNotIn("Cotton Shirt", csv_text)

    def test_dashboard_export_links_use_current_view_wording_and_query(self):
        self.client.login(username="testuser", password="testpass123")

        response = self.client.get(
            reverse("dashboard"),
            {
                "search": "drill",
                "supplier": "Acme Tools",
                "category": str(self.tools_category.id),
                "sort": "price",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Export CSV (Current View)")
        self.assertContains(response, "Export PDF (Current View)")
        self.assertContains(
            response,
            (
                f"/products/export/csv/?search=drill&amp;supplier=Acme+Tools"
                f"&amp;category={self.tools_category.id}&amp;sort=price"
            ),
        )

    def test_export_pdf_mirrors_active_filters(self):
        self.client.login(username="testuser", password="testpass123")
        Product.objects.create(
            owner=self.user,
            category=self.tools_category,
            name="PDF Match",
            sku="PDF-100",
            price=Decimal("30.00"),
            quantity=2,
            supplier="PagerCo",
        )
        Product.objects.create(
            owner=self.user,
            category=self.tools_category,
            name="PDF Miss",
            sku="PDF-101",
            price=Decimal("40.00"),
            quantity=3,
            supplier="OtherCo",
        )

        drawn_lines = []

        class FakeCanvas:
            def __init__(self, *args, **kwargs):
                pass

            def setFont(self, *args, **kwargs):
                pass

            def drawString(self, _x, _y, text):
                drawn_lines.append(text)

            def showPage(self):
                pass

            def save(self):
                pass

        with patch("invApp.views.canvas.Canvas", return_value=FakeCanvas()):
            response = self.client.get(
                reverse("export_products_pdf"),
                {"supplier": "PagerCo", "sort": "name"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        product_lines = [line for line in drawn_lines if "|" in line]
        self.assertEqual(len(product_lines), 1)
        self.assertIn("PDF Match", product_lines[0])
        self.assertNotIn("PDF Miss", product_lines[0])
        self.assertNotIn("Cotton Shirt", product_lines[0])

    def test_export_pdf_requires_authentication(self):
        response = self.client.get(reverse("export_products_pdf"))

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/login/"))

    def test_export_pdf_returns_pdf_attachment(self):
        self.client.login(username="testuser", password="testpass123")

        response = self.client.get(reverse("export_products_pdf"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn(
            "attachment; filename=products.pdf", response["Content-Disposition"]
        )
        self.assertTrue(response.content.startswith(b"%PDF"))

    def test_product_create_writes_activity_log(self):
        self.client.login(username="testuser", password="testpass123")

        response = self.client.post(
            reverse("product_create"),
            {
                "name": "Sneakers",
                "category": self.category.id,
                "sku": "SKU-1002",
                "price": "59.90",
                "quantity": 20,
                "supplier": "RunFast",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        created_product = Product.objects.get(owner=self.user, sku="SKU-1002")
        log = ActivityLog.objects.get(user=self.user, action=ActivityLog.ACTION_ADDED)
        self.assertEqual(log.product_id, created_product.product_id)
        self.assertIn("Added product Sneakers (SKU-1002)", log.details)

    def test_product_edit_writes_activity_log(self):
        self.client.login(username="testuser", password="testpass123")

        response = self.client.post(
            reverse("product_edit", args=[self.product.product_id]),
            {
                "name": "Cotton Shirt Updated",
                "category": self.category.id,
                "sku": "SKU-1001",
                "price": "24.99",
                "quantity": 55,
                "supplier": "ABC Corp",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        log = ActivityLog.objects.get(user=self.user, action=ActivityLog.ACTION_EDITED)
        self.assertEqual(log.product_id, self.product.product_id)
        self.assertIn("Edited product Cotton Shirt Updated (SKU-1001)", log.details)

    def test_product_delete_writes_activity_log(self):
        self.client.login(username="testuser", password="testpass123")

        response = self.client.post(
            reverse("product_delete", args=[self.product.product_id]),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        log = ActivityLog.objects.get(user=self.user, action=ActivityLog.ACTION_DELETED)
        self.assertIsNone(log.product)
        self.assertIn("Deleted product Cotton Shirt (SKU-1001)", log.details)

    def test_dashboard_activity_logs_are_scoped_to_current_user(self):
        ActivityLog.objects.create(
            user=self.user,
            product=self.product,
            action=ActivityLog.ACTION_ADDED,
            details="Visible log for owner",
        )
        ActivityLog.objects.create(
            user=self.other_user,
            product=self.other_product,
            action=ActivityLog.ACTION_ADDED,
            details="Hidden log for other user",
        )

        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Visible log for owner")
        self.assertNotContains(response, "Hidden log for other user")


class InventoryApiBoundaryTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user_a = User.objects.create_user("user_a", password="testpass123")
        self.user_b = User.objects.create_user("user_b", password="testpass123")
        self.category_a = Category.objects.create(owner=self.user_a, name="A Category")
        self.category_b = Category.objects.create(owner=self.user_b, name="B Category")
        self.product_a = Product.objects.create(
            owner=self.user_a,
            category=self.category_a,
            name="Item A",
            sku="A-001",
            price=Decimal("9.99"),
            quantity=4,
            supplier="A Supplier",
        )

    def test_api_rejects_other_users_category(self):
        self.client.force_authenticate(user=self.user_a)
        response = self.client.post(
            "/products/",
            {
                "name": "Bad Product",
                "category": self.category_b.id,
                "sku": "A-002",
                "price": "12.99",
                "quantity": 3,
                "supplier": "Supplier",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("category", response.data)

    def test_api_rejects_duplicate_sku_per_owner(self):
        self.client.force_authenticate(user=self.user_a)
        response = self.client.post(
            "/products/",
            {
                "name": "Duplicate",
                "category": self.category_a.id,
                "sku": "A-001",
                "price": "12.99",
                "quantity": 3,
                "supplier": "Supplier",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("sku", response.data)

    def test_api_rejects_duplicate_category_name_per_owner(self):
        self.client.force_authenticate(user=self.user_a)
        Category.objects.create(owner=self.user_a, name="Apparel")

        response = self.client.post(
            "/categories/",
            {"name": "apparel"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("name", response.data)
        self.assertEqual(
            response.data["name"][0],
            "You already have a category with this name.",
        )

    def test_api_duplicate_category_integrity_error_returns_clean_400(self):
        self.client.force_authenticate(user=self.user_a)
        Category.objects.create(owner=self.user_a, name="Apparel")

        with patch(
            "invApp.serializers.CategorySerializer.validate_name",
            autospec=True,
            side_effect=lambda _self, value: value,
        ):
            response = self.client.post(
                "/categories/",
                {"name": "Apparel"},
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("name", response.data)
        self.assertEqual(
            response.data["name"][0],
            "You already have a category with this name.",
        )

    def test_api_user_cannot_patch_another_users_product(self):
        self.client.force_authenticate(user=self.user_b)
        response = self.client.patch(
            f"/products/{self.product_a.product_id}/",
            {"name": "Intrusion"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_api_user_cannot_delete_another_users_product(self):
        self.client.force_authenticate(user=self.user_b)
        response = self.client.delete(f"/products/{self.product_a.product_id}/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Product.objects.filter(pk=self.product_a.pk).exists())

    def test_api_list_shows_only_owned_products(self):
        Product.objects.create(
            owner=self.user_b,
            category=self.category_b,
            name="Item B",
            sku="B-001",
            price=Decimal("7.50"),
            quantity=6,
            supplier="B Supplier",
        )
        self.client.force_authenticate(user=self.user_a)

        response = self.client.get("/products/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        product_ids = {item["product_id"] for item in response.data}
        self.assertIn(self.product_a.product_id, product_ids)
        self.assertEqual(len(product_ids), 1)

    def test_api_list_requires_authentication(self):
        unauth_client = APIClient()
        response = unauth_client.get("/products/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_api_rejects_invalid_price(self):
        self.client.force_authenticate(user=self.user_a)
        response = self.client.post(
            "/products/",
            {
                "name": "Invalid Price",
                "category": self.category_a.id,
                "sku": "A-003",
                "price": "0",
                "quantity": 3,
                "supplier": "Supplier",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("price", response.data)

    def test_api_rejects_invalid_quantity(self):
        self.client.force_authenticate(user=self.user_a)
        response = self.client.post(
            "/products/",
            {
                "name": "Invalid Qty",
                "category": self.category_a.id,
                "sku": "A-004",
                "price": "15.50",
                "quantity": -1,
                "supplier": "Supplier",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("quantity", response.data)


class InventoryApiObjectPermissionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner_user = User.objects.create_user("owner_user", password="testpass123")
        self.other_user = User.objects.create_user("other_user", password="testpass123")

        self.owner_category = Category.objects.create(
            owner=self.owner_user,
            name="Owner Category",
        )
        self.other_category = Category.objects.create(
            owner=self.other_user,
            name="Other Category",
        )

        self.owner_product = Product.objects.create(
            owner=self.owner_user,
            category=self.owner_category,
            name="Owner Product",
            sku="OWNER-001",
            price=Decimal("10.00"),
            quantity=5,
            supplier="Owner Supplier",
        )
        self.other_product = Product.objects.create(
            owner=self.other_user,
            category=self.other_category,
            name="Other Product",
            sku="OTHER-001",
            price=Decimal("20.00"),
            quantity=7,
            supplier="Other Supplier",
        )

    def test_products_list_returns_only_owned_objects(self):
        self.client.force_authenticate(user=self.owner_user)

        response = self.client.get("/products/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        product_ids = {item["product_id"] for item in response.data}
        self.assertIn(self.owner_product.product_id, product_ids)
        self.assertNotIn(self.other_product.product_id, product_ids)

    def test_products_retrieve_respects_object_permission(self):
        self.client.force_authenticate(user=self.owner_user)

        own_response = self.client.get(f"/products/{self.owner_product.product_id}/")
        other_response = self.client.get(f"/products/{self.other_product.product_id}/")

        self.assertEqual(own_response.status_code, status.HTTP_200_OK)
        self.assertEqual(other_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_products_update_respects_object_permission(self):
        self.client.force_authenticate(user=self.owner_user)

        own_response = self.client.patch(
            f"/products/{self.owner_product.product_id}/",
            {"name": "Owner Product Updated"},
            format="json",
        )
        other_response = self.client.patch(
            f"/products/{self.other_product.product_id}/",
            {"name": "Intrusion Attempt"},
            format="json",
        )

        self.assertEqual(own_response.status_code, status.HTTP_200_OK)
        self.assertEqual(other_response.status_code, status.HTTP_404_NOT_FOUND)
        self.owner_product.refresh_from_db()
        self.other_product.refresh_from_db()
        self.assertEqual(self.owner_product.name, "Owner Product Updated")
        self.assertEqual(self.other_product.name, "Other Product")

    def test_products_delete_respects_object_permission(self):
        self.client.force_authenticate(user=self.owner_user)

        own_response = self.client.delete(f"/products/{self.owner_product.product_id}/")
        other_response = self.client.delete(
            f"/products/{self.other_product.product_id}/"
        )

        self.assertEqual(own_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(other_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(Product.objects.filter(pk=self.owner_product.pk).exists())
        self.assertTrue(Product.objects.filter(pk=self.other_product.pk).exists())

    def test_categories_list_returns_only_owned_objects(self):
        self.client.force_authenticate(user=self.owner_user)

        response = self.client.get("/categories/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        category_ids = {item["id"] for item in response.data}
        self.assertIn(self.owner_category.id, category_ids)
        self.assertNotIn(self.other_category.id, category_ids)

    def test_categories_retrieve_respects_object_permission(self):
        self.client.force_authenticate(user=self.owner_user)

        own_response = self.client.get(f"/categories/{self.owner_category.id}/")
        other_response = self.client.get(f"/categories/{self.other_category.id}/")

        self.assertEqual(own_response.status_code, status.HTTP_200_OK)
        self.assertEqual(other_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_categories_update_respects_object_permission(self):
        self.client.force_authenticate(user=self.owner_user)

        own_response = self.client.patch(
            f"/categories/{self.owner_category.id}/",
            {"name": "Owner Category Updated"},
            format="json",
        )
        other_response = self.client.patch(
            f"/categories/{self.other_category.id}/",
            {"name": "Intrusion Attempt"},
            format="json",
        )

        self.assertEqual(own_response.status_code, status.HTTP_200_OK)
        self.assertEqual(other_response.status_code, status.HTTP_404_NOT_FOUND)
        self.owner_category.refresh_from_db()
        self.other_category.refresh_from_db()
        self.assertEqual(self.owner_category.name, "Owner Category Updated")
        self.assertEqual(self.other_category.name, "Other Category")

    def test_categories_delete_respects_object_permission(self):
        self.client.force_authenticate(user=self.owner_user)

        own_response = self.client.delete(f"/categories/{self.owner_category.id}/")
        other_response = self.client.delete(f"/categories/{self.other_category.id}/")

        self.assertEqual(own_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(other_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(Category.objects.filter(pk=self.owner_category.pk).exists())
        self.assertTrue(Category.objects.filter(pk=self.other_category.pk).exists())
