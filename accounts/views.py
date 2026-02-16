import re
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.shortcuts import render, redirect


def password_errors(pw: str) -> list[str]:
    errs = []
    if len(pw) < 6:
        errs.append("La contraseña debe tener mínimo 6 caracteres.")
    if not re.search(r"[A-Z]", pw):
        errs.append("La contraseña debe incluir al menos 1 letra MAYÚSCULA.")
    if not re.search(r"[a-z]", pw):
        errs.append("La contraseña debe incluir al menos 1 letra minúscula.")
    if not re.search(r"\d", pw):
        errs.append("La contraseña debe incluir al menos 1 número.")
    if not re.search(r"[^\w\s]", pw):
        errs.append("La contraseña debe incluir al menos 1 carácter especial (ej: !@#$%).")
    return errs


def home_redirect(request):
    return redirect("dashboard" if request.user.is_authenticated else "login")


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        username_or_email = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()

        errors = []
        if not username_or_email:
            errors.append("Escribe tu usuario o correo.")
        if not password:
            errors.append("Escribe tu contraseña.")

        if errors:
            for e in errors:
                messages.error(request, e)
            return render(request, "accounts/login.html", {
                "username_value": username_or_email,
            })

        # si parece email, validarlo y convertir a username
        username = username_or_email
        if "@" in username_or_email:
            try:
                validate_email(username_or_email)
            except ValidationError:
                messages.error(request, "El correo no tiene un formato válido.")
                return render(request, "accounts/login.html", {
                    "username_value": username_or_email,
                })

            u = User.objects.filter(email__iexact=username_or_email).first()
            if not u:
                messages.error(request, "No existe una cuenta con ese correo.")
                return render(request, "accounts/login.html", {
                    "username_value": username_or_email,
                })
            username = u.username

        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            messages.success(request, f"Bienvenido, {user.username} ")
            return redirect("dashboard")

        messages.error(request, "Usuario/correo o contraseña incorrectos.")
        return render(request, "accounts/login.html", {
            "username_value": username_or_email,
        })

    return render(request, "accounts/login.html")


def register_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "").strip()

        errors = []
        if not username:
            errors.append("El usuario es obligatorio.")
        if not email:
            errors.append("El correo es obligatorio.")
        if not password:
            errors.append("La contraseña es obligatoria.")

        if email:
            try:
                validate_email(email)
            except ValidationError:
                errors.append("El correo no tiene un formato válido.")

        if username and len(username) < 3:
            errors.append("El usuario debe tener al menos 3 caracteres.")

        if username and User.objects.filter(username__iexact=username).exists():
            errors.append("Ese usuario ya existe.")

        if email and User.objects.filter(email__iexact=email).exists():
            errors.append("Ese correo ya está registrado.")

        if password:
            errors.extend(password_errors(password))

        if errors:
            for e in errors:
                messages.error(request, e)
            return render(request, "accounts/register.html", {
                "username_value": username,
                "email_value": email,
            })

        User.objects.create_user(username=username, email=email, password=password)
        messages.success(request, "Cuenta creada Ahora inicia sesión.")
        return redirect("login")

    return render(request, "accounts/register.html")


def logout_view(request):
    logout(request)
    messages.info(request, "Sesión cerrada.")
    return redirect("login")
