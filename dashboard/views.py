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
from django.http import StreamingHttpResponse
import cv2
import time
from django.http import StreamingHttpResponse
from django.core.cache import cache
import time
from inference.live_session import LiveEvalSession

from dataclasses import dataclass
from datetime import date
from typing import Dict, List
from django.db.models import Count, Sum, IntegerField, Case, When
from django.db.models.functions import TruncMonth
from django.utils import timezone


# ========= Inicio: Vistas SideBar =============

TEMPLATE = "dashboard/index.html"


@login_required(login_url="login")
def dashboard_view(request):
    return render(request, TEMPLATE, {
        "page_title": "Dashboard",
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


# ===== Inicio: Camera streaming (MJPEG) =====

CAMERA_RTSP = {
    "cam1": "rtsp://192.168.100.10:8554/live/gopro",  # GoPro actual la ip cambia cada vez
    "cam2": None,  # futura cámara
}

def _mjpeg_generator(rtsp_url: str):
    cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)

    # reintenta si no abre
    while not cap.isOpened():
        time.sleep(1)
        cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)

    while True:
        ok, frame = cap.read()
        if not ok:
            time.sleep(0.05)
            continue

        ok, jpg = cv2.imencode(".jpg", frame)
        if not ok:
            continue

        yield (b"--frame\r\n"
               b"Content-Type: image/jpeg\r\n\r\n" + jpg.tobytes() + b"\r\n")


@login_required(login_url="login")
def camera_stream(request, cam_id: str):
    rtsp_url = CAMERA_RTSP.get(cam_id)

    if not rtsp_url:
        return JsonResponse({"ok": False, "error": "Cámara no configurada."}, status=404)

    return StreamingHttpResponse(
        _mjpeg_generator(rtsp_url),
        content_type="multipart/x-mixed-replace; boundary=frame"
    )

# ===== Fin: Camera streaming (MJPEG) =====

# ===== Inicio: Quality/Live sessions Camera =====

LIVE_SESSIONS = {}

# reutiliza mapeo RTSP
CAMERA_RTSP = {
    "cam1": "rtsp://192.168.100.10:8554/live/gopro", # cambia la ip cada vez que se pruebe
    "cam2": None,
}

@login_required(login_url="login")
def live_annotated_stream(request, cam_id: str):
    """
    Stream MJPEG del frame anotado por la sesión (cajas+labels+ID).
    Si no hay sesión corriendo, devuelve 404 para que UI muestre placeholder.
    """
    sess: LiveEvalSession | None = LIVE_SESSIONS.get(cam_id)
    if not sess or sess.status()["state"] not in ("running", "finished"):
        return JsonResponse({"ok": False, "error": "No hay sesión activa."}, status=404)

    def gen():
        while True:
            st = sess.status()["state"]
            jpg = sess.get_latest_jpeg()
            if jpg:
                yield (b"--frame\r\n"
                       b"Content-Type: image/jpeg\r\n\r\n" + jpg + b"\r\n")
            else:
                time.sleep(0.05)

            # si terminó, seguimos emitiendo el último frame unos segundos o hasta que el navegador cierre
            if st in ("finished", "error"):
                time.sleep(0.05)

    return StreamingHttpResponse(gen(), content_type="multipart/x-mixed-replace; boundary=frame")

@login_required(login_url="login")
@require_POST
@csrf_protect
def live_start(request):
    cam_id = request.POST.get("cam_id", "cam1")
    batch_id = request.POST.get("batch_id")

    if not batch_id:
        return JsonResponse({"ok": False, "error": "Falta batch_id."}, status=400)

    batch = get_object_or_404(Batch, pk=batch_id)

    # No duplicar evaluación guardada
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

    rtsp = CAMERA_RTSP.get(cam_id)
    if not rtsp:
        return JsonResponse({"ok": False, "error": "Cámara no configurada."}, status=400)

    # crea / reinicia sesión
    old = LIVE_SESSIONS.get(cam_id)
    if old:
        try:
            old.stop()
        except:
            pass

    sess = LiveEvalSession(
        rtsp_url=rtsp,
        duration_s=30,
        conf_display=0.35,
        conf_count=0.50,
        min_frames_confirm=5,
        tracker_cfg="bytetrack.yaml",
    )
    sess.batch_id = int(batch.id)  # amarra la sesión al lote

    LIVE_SESSIONS[cam_id] = sess

    sess.start()

    return JsonResponse({"ok": True, "state": "running", "cam_id": cam_id, "duration_s": 30})


@login_required(login_url="login")
@require_POST
@csrf_protect
def live_stop(request):
    cam_id = request.POST.get("cam_id", "cam1")
    sess: LiveEvalSession | None = LIVE_SESSIONS.get(cam_id)
    if not sess:
        return JsonResponse({"ok": False, "error": "No hay sesión."}, status=404)

    sess.stop()
    return JsonResponse({"ok": True})


@login_required(login_url="login")
def live_status(request):
    cam_id = request.GET.get("cam_id", "cam1")
    batch_id = request.GET.get("batch_id")

    sess: LiveEvalSession | None = LIVE_SESSIONS.get(cam_id)
    if not sess:
        return JsonResponse({"ok": True, "state": "idle"})

    try:
        req_batch = int(batch_id) if batch_id else None
    except:
        req_batch = None

    if req_batch is not None and getattr(sess, "batch_id", None) != req_batch:
        return JsonResponse({"ok": True, "state": "idle"})

    return JsonResponse({"ok": True, **sess.status()})


@login_required(login_url="login")
@require_POST
@csrf_protect
def live_save(request):
    cam_id = request.POST.get("cam_id", "cam1")
    sess: LiveEvalSession | None = LIVE_SESSIONS.get(cam_id)
    if not sess:
        return JsonResponse({"ok": False, "error": "No hay sesión."}, status=404)

    st = sess.status()
    if st["state"] != "finished":
        return JsonResponse({"ok": False, "error": "La sesión aún no ha terminado."}, status=400)

    payload = st["final"] or {}
    if not payload:
        return JsonResponse({"ok": False, "error": "No hay resultados."}, status=400)

    batch_id = getattr(sess, "batch_id", None)
    if not batch_id:
        return JsonResponse({"ok": False, "error": "Sesión sin batch ligado."}, status=400)

    batch = get_object_or_404(Batch, pk=batch_id)
    if hasattr(batch, "evaluation"):
        return JsonResponse({"ok": True, "already_evaluated": True})

    counts_raw = payload.get("counts") or {}
    # Normaliza a tu formato primary/secondary (reusa tu helper actual)
    counts = normalize_counts_from_model({"counts": counts_raw})

    primary_total = int(payload.get("primary_total") or 0)
    secondary_total = int(payload.get("secondary_total") or 0)
    defects_total = primary_total + secondary_total
    grade = payload.get("grade")
    score = payload.get("score")

    with transaction.atomic():
        ev = Evaluation.objects.create(
            batch=batch,
            method=Evaluation.METHOD_CAMERA,
            grade=grade,
            score=score,
            counts=counts,
            primary_total=primary_total,
            secondary_total=secondary_total,
            defects_total=defects_total,
        )

    # detener y limpiar sesión para que no se "pegue" a otros lotes
    try:
        sess.stop()
    except Exception:
        pass

    LIVE_SESSIONS.pop(cam_id, None)
    cache.delete(f"live_batch:{cam_id}")

    return JsonResponse({
        "ok": True,
        "grade": ev.grade,
        "score": float(ev.score) if ev.score is not None else None,
        "primary_total": ev.primary_total,
        "secondary_total": ev.secondary_total,
        "defects_total": ev.defects_total,
        "counts": ev.counts,
    })

# ===== Fin: Quality/Live sessions Camera =====

# ===== Inicio: Graficas Dashboard =====

MONTH_NAMES_ES = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]


def _safe_pct(num: float, den: float) -> float:
    if den <= 0:
        return 0.0
    return round((num / den) * 100.0, 2)


def _year_month_bounds(year: int, month: int) -> tuple[date, date]:
    # inicio mes, inicio mes siguiente
    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, month + 1, 1)
    return start, end


def dashboard_summary_api(request):
    now = timezone.localtime(timezone.now())
    year = now.year
    current_month = now.month
    prev_month = current_month - 1 if current_month > 1 else 12
    prev_year = year if current_month > 1 else year - 1

    # ========= 1) Series por mes =========
    monthly_qs = (
        Evaluation.objects
        .filter(created_at__year=year)
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(
            lots=Count("id"),
            kg=Sum("batch__weight_kg"),
            accepted=Count(Case(When(grade__in=[1, 2], then=1), output_field=IntegerField())),
            total=Count("id"),
        )
        .order_by("month")
    )

    # Rellenar meses faltantes (1..12) con 0
    lots_by_month = {m: 0 for m in range(1, 13)}
    kg_by_month = {m: 0.0 for m in range(1, 13)}
    acc_by_month = {m: 0 for m in range(1, 13)}
    total_by_month = {m: 0 for m in range(1, 13)}

    for row in monthly_qs:
        month_num = row["month"].month
        lots_by_month[month_num] = int(row["lots"] or 0)
        kg_by_month[month_num] = float(row["kg"] or 0.0)
        acc_by_month[month_num] = int(row["accepted"] or 0)
        total_by_month[month_num] = int(row["total"] or 0)

    labels = MONTH_NAMES_ES
    lots_series = [lots_by_month[m] for m in range(1, 13)]
    kg_series = [round(kg_by_month[m], 2) for m in range(1, 13)]

    # ========= 2) KPIs globales =========
    global_qs = Evaluation.objects.all().aggregate(
        total_lots=Count("id"),
        total_kg=Sum("batch__weight_kg"),
        accepted=Count(Case(When(grade__in=[1, 2], then=1), output_field=IntegerField())),
        rejected=Count(Case(When(grade=4, then=1), output_field=IntegerField())),
    )

    total_lots = int(global_qs["total_lots"] or 0)
    total_kg = float(global_qs["total_kg"] or 0.0)
    accepted = int(global_qs["accepted"] or 0)
    rejected = int(global_qs["rejected"] or 0)

    quality_pct = _safe_pct(accepted, total_lots)
    reject_pct = _safe_pct(rejected, total_lots)

    # ========= 3) Comparativa mes actual vs anterior =========
    cur_start, cur_end = _year_month_bounds(year, current_month)
    prev_start, prev_end = _year_month_bounds(prev_year, prev_month)

    cur = Evaluation.objects.filter(created_at__date__gte=cur_start, created_at__date__lt=cur_end).aggregate(
        lots=Count("id"),
        kg=Sum("batch__weight_kg"),
        accepted=Count(Case(When(grade__in=[1, 2], then=1), output_field=IntegerField())),
    )
    prev = Evaluation.objects.filter(created_at__date__gte=prev_start, created_at__date__lt=prev_end).aggregate(
        lots=Count("id"),
        kg=Sum("batch__weight_kg"),
        accepted=Count(Case(When(grade__in=[1, 2], then=1), output_field=IntegerField())),
    )

    cur_lots = int(cur["lots"] or 0)
    prev_lots = int(prev["lots"] or 0)

    cur_kg = float(cur["kg"] or 0.0)
    prev_kg = float(prev["kg"] or 0.0)

    cur_quality = _safe_pct(int(cur["accepted"] or 0), cur_lots)
    prev_quality = _safe_pct(int(prev["accepted"] or 0), prev_lots)

    def delta_pct(cur_val: float, prev_val: float) -> float:
        if prev_val == 0:
            return 0.0 if cur_val == 0 else 100.0
        return round(((cur_val - prev_val) / prev_val) * 100.0, 2)

    comparison = {
        "current": {"year": year, "month": current_month},
        "previous": {"year": prev_year, "month": prev_month},
        "lots": {"current": cur_lots, "previous": prev_lots, "delta_pct": delta_pct(cur_lots, prev_lots)},
        "kg": {"current": round(cur_kg, 2), "previous": round(prev_kg, 2), "delta_pct": delta_pct(cur_kg, prev_kg)},
        "quality": {
            "current": cur_quality,
            "previous": prev_quality,
            "delta_points": round(cur_quality - prev_quality, 2),
        },
    }

    payload = {
        "year": year,
        "has_data": total_lots > 0,
        "kpis": {
            "total_lots": total_lots,
            "total_kg": round(total_kg, 2),
            "quality_pct": quality_pct,
            "reject_pct": reject_pct,
        },
        "charts": {
            "labels": labels,
            "lots_by_month": lots_series,
            "kg_by_month": kg_series,
        },
        "comparison": comparison,
    }
    return JsonResponse(payload)

# ===== Fin: Graficas Dashboard =====