from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

app_name = "dashboard"

urlpatterns = [
    path("", views.dashboard_view, name="dashboard"),
    path("api/dashboard/summary/", views.dashboard_summary_api, name="summary_api"),
    path("camera/", views.camera_view, name="camera"),
    path("camera/stream/<str:cam_id>/", views.camera_stream, name="camera_stream"),
    path("live/start/", views.live_start, name="live_start"),
    path("live/stop/", views.live_stop, name="live_stop"),
    path("live/status/", views.live_status, name="live_status"),
    path("live/save/", views.live_save, name="live_save"),
    path("live/stream/<str:cam_id>/", views.live_annotated_stream, name="live_stream"),
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
