from django.contrib.auth.decorators import login_required
from django.shortcuts import render

TEMPLATE = "dashboard/index.html"

@login_required(login_url="login")
def dashboard_view(request):
    return render(request, TEMPLATE, {
        "page_title": "Estadísticas",
        "active": "dashboard",
    })

@login_required(login_url="login")
def camera_view(request):
    return render(request, TEMPLATE, {
        "page_title": "Camera monitoring",
        "active": "camera",
    })

@login_required(login_url="login")
def quality_view(request):
    return render(request, TEMPLATE, {
        "page_title": "Quality assessment",
        "active": "quality",
    })

@login_required(login_url="login")
def batch_metrics_view(request):
    return render(request, TEMPLATE, {
        "page_title": "Batch metrics",
        "active": "batch",
    })

@login_required(login_url="login")
def packaging_view(request):
    return render(request, TEMPLATE, {
        "page_title": "Packaging and distribution",
        "active": "packaging",
    })

@login_required(login_url="login")
def activity_log_view(request):
    return render(request, TEMPLATE, {
        "page_title": "Activity Log",
        "active": "activity",
    })

@login_required(login_url="login")
def reports_view(request):
    return render(request, TEMPLATE, {
        "page_title": "Report generation",
        "active": "reports",
    })

@login_required(login_url="login")
def alerts_view(request):
    return render(request, TEMPLATE, {
        "page_title": "Alerts and notifications",
        "active": "alerts",
    })

@login_required(login_url="login")
def settings_view(request):
    return render(request, TEMPLATE, {
        "page_title": "System settings",
        "active": "settings",
    })
