from django.contrib import admin
from django.urls import path, include
from accounts import views as v
from dashboard.views import dashboard_view
from django.contrib.auth import views as auth_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", v.home_redirect, name="home"),
    path("login/", v.login_view, name="login"),
    path("register/", v.register_view, name="register"),
    path("logout/", v.logout_view, name="logout"),
    path("dashboard/", dashboard_view, name="dashboard"),
    path("dashboard/", include("dashboard.urls")),
    path("password-reset/", auth_views.PasswordResetView.as_view(
        template_name="accounts/password_reset.html",
        email_template_name="accounts/password_reset_email.txt",
        subject_template_name="accounts/password_reset_subject.txt",
        success_url="/password-reset/done/",
    ), name="password_reset"),
    path("password-reset/done/", auth_views.PasswordResetDoneView.as_view(
        template_name="accounts/password_reset_done.html"
    ), name="password_reset_done"),
    path("reset/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(
        template_name="accounts/password_reset_confirm.html",
        success_url="/reset/done/",
    ), name="password_reset_confirm"),
    path("reset/done/", auth_views.PasswordResetCompleteView.as_view(
        template_name="accounts/password_reset_complete.html"
    ), name="password_reset_complete"),
]
