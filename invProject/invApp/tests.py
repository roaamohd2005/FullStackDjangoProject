from decimal import Decimal

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
