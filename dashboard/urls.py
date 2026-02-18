from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

app_name = "dashboard"

urlpatterns = [
    path("", views.dashboard_view, name="dashboard"),
    path("camera/", views.camera_view, name="camera"),
    path("quality/", views.quality_home, name="quality"),
    path("quality/batch/<int:batch_id>/", views.quality_batch_detail, name="quality_batch_detail"),
    path("batch/", views.batch_metrics_view, name="batch"),
    path("packaging/", views.packaging_view, name="packaging"),
    path("activity/", views.activity_log_view, name="activity"),
    path("reports/", views.reports_view, name="reports"),
    path("alerts/", views.alerts_view, name="alerts"),
    path("settings/", views.settings_view, name="settings"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("quality/evaluate/", views.evaluate_image, name="quality_evaluate"),
    path("settings/providers/", views.settings_providers, name="settings_providers"),
]
