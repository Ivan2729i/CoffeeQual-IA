from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from inference.analyze import analyze_image
import os
import tempfile
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.db import transaction

from .models import Batch, Provider, Evaluation
from .forms import ProviderForm, BatchCreateForm


# ========= Inicio: Vistas SideBar =============

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


# ========= Fin: Vistas SideBar =============


# ========= Inicio: Settings/Providers =============

@login_required(login_url="login")
@require_http_methods(["GET", "POST"])
def settings_providers(request):
    if request.method == "POST":
        form = ProviderForm(request.POST)
        if form.is_valid():
            p = form.save()
            messages.success(request, f"Proveedor '{p}' creado.")
            return redirect("dashboard:settings_providers")

        messages.error(request, "No se pudo guardar. Revisa los campos marcados.")
    else:
        form = ProviderForm()

    providers = Provider.objects.order_by("-created_at")
    return render(request, TEMPLATE, {
        "page_title": "System settings",
        "active": "settings",
        "settings_section": "providers",
        "form": form,
        "providers": providers,
    })


# ========= Fin: Settings/Providers =============


# ========= Inicio: Quality helpers =============

PRIMARY_DEFECTS = {"black", "foreign", "infested", "sour"}
SECONDARY_DEFECTS = {"broken", "fraghusk", "husk", "immature", "green"}


def normalize_counts_from_model(res: dict) -> dict:
    if not isinstance(res, dict):
        return {"primary": {}, "secondary": {}}

    c = res.get("counts") or {}

    if isinstance(c, dict) and ("primary" in c or "secondary" in c):
        return {
            "primary": dict(c.get("primary") or {}),
            "secondary": dict(c.get("secondary") or {}),
        }

    if isinstance(c, dict):
        out = {"primary": {}, "secondary": {}}
        for name, val in c.items():
            try:
                n = int(val)
            except:
                n = 0
            if n <= 0:
                continue

            if name in PRIMARY_DEFECTS:
                out["primary"][name] = n
            elif name in SECONDARY_DEFECTS:
                out["secondary"][name] = n
            else:
                out["secondary"][name] = n

        return out

    return {"primary": {}, "secondary": {}}


def totals_from_counts(counts: dict) -> tuple[int, int, int]:
    p = counts.get("primary") or {}
    s = counts.get("secondary") or {}

    def safe_sum(d):
        total = 0
        for v in d.values():
            try:
                total += int(v)
            except:
                pass
        return total

    primary_total = safe_sum(p)
    secondary_total = safe_sum(s)
    return primary_total, secondary_total, primary_total + secondary_total


# ========= Fin: Quality helpers =============


# ========= Inicio: Quality =============

@login_required(login_url="login")
@require_POST
@csrf_protect
def evaluate_image(request):
    batch_id = request.POST.get("batch_id")
    if not batch_id:
        return JsonResponse({"ok": False, "error": "Falta batch_id."}, status=400)

    batch = get_object_or_404(Batch, pk=batch_id)

    # Si ya tiene evaluación, no duplicar
    if hasattr(batch, "evaluation"):
        ev = batch.evaluation
        return JsonResponse({
            "ok": True,
            "already_evaluated": True,
            "grade": ev.grade,
            "score": float(ev.score) if ev.score is not None else None,
            "primary_total": ev.primary_total,
            "secondary_total": ev.secondary_total,
            "defects_total": ev.defects_total,
            "counts": ev.counts,
        })

    f = request.FILES.get("image")
    if not f:
        return JsonResponse({"ok": False, "error": "Falta el archivo 'image'."}, status=400)

    tmp_path = None
    try:
        fd, tmp_path = tempfile.mkstemp(suffix=".jpg")
        with os.fdopen(fd, "wb") as tmp:
            for chunk in f.chunks():
                tmp.write(chunk)

        # IA
        res = analyze_image(tmp_path, conf=0.25)
        print("IA RES:", res)  # <- verás esto en la consola del servidor

        if not isinstance(res, dict):
            return JsonResponse({"ok": False, "error": "Respuesta inválida del modelo."}, status=500)

        counts = normalize_counts_from_model(res)

        # totales: usar los del modelo si vienen, si no, calcularlos
        primary_total = res.get("primary_total")
        secondary_total = res.get("secondary_total")

        if primary_total is None or secondary_total is None:
            p, s, t = totals_from_counts(counts)
            primary_total, secondary_total, defects_total = p, s, t
        else:
            try:
                primary_total = int(primary_total)
            except:
                primary_total = 0
            try:
                secondary_total = int(secondary_total)
            except:
                secondary_total = 0
            defects_total = primary_total + secondary_total

        grade = res.get("grade")
        score = res.get("score")

        with transaction.atomic():
            ev = Evaluation.objects.create(
                batch=batch,
                method=Evaluation.METHOD_IMAGE,
                grade=grade,
                score=score,
                counts=counts,
                primary_total=primary_total,
                secondary_total=secondary_total,
                defects_total=defects_total,
            )

        return JsonResponse({
            "ok": True,
            "already_evaluated": False,
            "grade": ev.grade,
            "score": float(ev.score) if ev.score is not None else None,
            "primary_total": ev.primary_total,
            "secondary_total": ev.secondary_total,
            "defects_total": ev.defects_total,
            "counts": ev.counts,
        })

    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)

    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except:
                pass


@login_required(login_url="login")
@require_http_methods(["GET", "POST"])
def quality_home(request):
    if request.method == "POST":
        form = BatchCreateForm(request.POST)
        if form.is_valid():
            batch = form.save()
            messages.success(request, f"Lote {batch.code} creado.")
            return redirect("dashboard:quality_batch_detail", batch_id=batch.id)
        messages.error(request, "No se pudo crear el lote. Revisa los campos.")
    else:
        form = BatchCreateForm()

    batches = Batch.objects.select_related("provider").order_by("-created_at")

    return render(request, TEMPLATE, {
        "page_title": "Quality assessment",
        "active": "quality",
        "quality_section": "home",
        "form": form,
        "batches": batches,
    })


@login_required(login_url="login")
def quality_batch_detail(request, batch_id: int):
    batch = get_object_or_404(Batch.objects.select_related("provider"), pk=batch_id)
    evaluation = batch.evaluation if hasattr(batch, "evaluation") else None

    return render(request, TEMPLATE, {
        "page_title": "Quality assessment",
        "active": "quality",
        "quality_section": "detail",
        "batch": batch,
        "evaluation": evaluation,
    })


# ========= Fin: Quality =============
