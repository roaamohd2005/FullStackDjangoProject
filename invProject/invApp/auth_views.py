from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

User = get_user_model()


def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip().lower()
        password1 = request.POST.get("password1", "")
        password2 = request.POST.get("password2", "")

        errors = []

        if not username:
            errors.append("Username is required.")
        if User.objects.filter(username=username).exists():
            errors.append("Username already taken.")
        if not email:
            errors.append("Email is required.")
        if User.objects.filter(email=email).exists():
            errors.append("Email already registered.")
        if len(password1) < 6:
            errors.append("Password must be at least 6 characters.")
        if password1 != password2:
            errors.append("Passwords do not match.")

        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            user = User.objects.create_user(
                username=username, email=email, password=password1
            )
            login(request, user)
            messages.success(request, f"Welcome, {username}!")
            return redirect("dashboard")

    return render(request, "invApp/auth/register.html")


def user_login(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        identifier = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        username = identifier

        if "@" in identifier:
            matched_user = User.objects.filter(email__iexact=identifier).first()
            if matched_user is not None:
                username = matched_user.username

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            return redirect("dashboard")
        else:
            messages.error(request, "Invalid username/email or password.")

    return render(request, "invApp/auth/login.html")


@login_required(login_url="login")
def user_logout(request):
    if request.method != "POST":
        messages.warning(request, "Logout must be confirmed with the button.")
        return redirect("dashboard")

    logout(request)
    messages.info(request, "Logged out. See you soon!")
    return redirect("login")
