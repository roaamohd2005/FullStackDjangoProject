from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Product


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

        logout_response = self.client.get(reverse("logout"), follow=True)
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


class InventoryViewsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        Product.objects.create(
            name="Cotton Shirt",
            sku="SKU-1001",
            price=24.99,
            quantity=50,
            supplier="ABC Corp",
        )

    def test_dashboard_redirects_unauthenticated(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/login/"))

    def test_dashboard_renders_authenticated(self):
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Inventory Pulse")

    def test_create_product_authenticated(self):
        self.client.login(username="testuser", password="testpass123")
        response = self.client.post(
            reverse("product_create"),
            {
                "name": "Sneakers",
                "sku": "SKU-1002",
                "price": 59.9,
                "quantity": 20,
                "supplier": "RunFast",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Product.objects.filter(sku="SKU-1002").exists())

    def test_chart_api_authenticated(self):
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("stock_chart_data"))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("labels", payload)
        self.assertIn("quantities", payload)
