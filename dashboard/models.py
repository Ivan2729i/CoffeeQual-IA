from django.db import models
from django.db.models import Q
from decimal import Decimal
from django.core.validators import MinValueValidator


class Provider(models.Model):
    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=120)
    contact = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Proveedor"
        verbose_name_plural = "Proveedores"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()


class Batch(models.Model):
    STATUS_DRAFT = "draft"
    STATUS_EVALUATED = "evaluated"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Borrador"),
        (STATUS_EVALUATED, "Evaluado"),
    ]

    code = models.CharField(
        max_length=12,
        unique=True,
        db_index=True,
        editable=False,
    )
    provider = models.ForeignKey(
        Provider,
        on_delete=models.PROTECT,
        related_name="batches",
    )
    weight_kg = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))]
    )
    created_at = models.DateTimeField(auto_now_add=True)

    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_DRAFT)

    class Meta:
        verbose_name = "Lote"
        verbose_name_plural = "Lotes"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.code

    def save(self, *args, **kwargs):
        creating = self.pk is None
        if creating and not self.code:
            self.code = self._generate_next_code()

        super().save(*args, **kwargs)

        if hasattr(self, "evaluation") and self.status != self.STATUS_EVALUATED:
            Batch.objects.filter(pk=self.pk).update(status=self.STATUS_EVALUATED)

    @staticmethod
    def _generate_next_code() -> str:
        last = Batch.objects.order_by("-id").first()
        next_num = (last.id + 1) if last else 1
        return f"L-{next_num:04d}"

    @property
    def is_evaluated(self) -> bool:
        return hasattr(self, "evaluation")


class Evaluation(models.Model):
    METHOD_IMAGE = "image"
    METHOD_CAMERA = "camera"
    METHOD_CHOICES = [
        (METHOD_IMAGE, "Imagen"),
        (METHOD_CAMERA, "Cámara"),
    ]

    batch = models.OneToOneField(
        Batch,
        on_delete=models.CASCADE,
        related_name="evaluation",
    )

    method = models.CharField(max_length=16, choices=METHOD_CHOICES, default=METHOD_IMAGE)

    # Grado 1-4
    grade = models.PositiveSmallIntegerField(null=True, blank=True)

    # Puntaje
    score = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    # Totales
    primary_total = models.PositiveIntegerField(default=0)
    secondary_total = models.PositiveIntegerField(default=0)
    defects_total = models.PositiveIntegerField(default=0)

    counts = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Evaluación"
        verbose_name_plural = "Evaluaciones"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(grade__isnull=True) | Q(grade__gte=1, grade__lte=4),
                name="evaluation_grade_between_1_and_4_or_null",
            )
        ]

    def __str__(self) -> str:
        return f"Evaluación {self.batch.code}"

    def recompute_totals_from_counts(self):
        data = self.counts or {}
        p = data.get("primary", {}) or {}
        s = data.get("secondary", {}) or {}

        primary_total = 0
        for v in p.values():
            if v is None:
                continue
            primary_total += int(v)

        secondary_total = 0
        for v in s.values():
            if v is None:
                continue
            secondary_total += int(v)

        self.primary_total = primary_total
        self.secondary_total = secondary_total
        self.defects_total = primary_total + secondary_total

    def save(self, *args, **kwargs):
        self.recompute_totals_from_counts()

        super().save(*args, **kwargs)

        Batch.objects.filter(pk=self.batch_id).update(status=Batch.STATUS_EVALUATED)
