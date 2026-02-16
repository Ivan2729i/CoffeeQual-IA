from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

app_name = "dashboard"

urlpatterns = [
    path("", views.dashboard_view, name="dashboard"),
    path("camera/", views.camera_view, name="camera"),
    path("quality/", views.quality_view, name="quality"),
    path("batch/", views.batch_metrics_view, name="batch"),
    path("packaging/", views.packaging_view, name="packaging"),
    path("activity/", views.activity_log_view, name="activity"),
    path("reports/", views.reports_view, name="reports"),
    path("alerts/", views.alerts_view, name="alerts"),
    path("settings/", views.settings_view, name="settings"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
]
