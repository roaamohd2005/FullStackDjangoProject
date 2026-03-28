from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import RegistrationForm

User = get_user_model()


def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    form = RegistrationForm(request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Welcome, {user.username}!")
            return redirect("dashboard")

    return render(request, "invApp/auth/register.html", {"form": form})


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
