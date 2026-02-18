import re
from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from .models import Provider, Batch
from decimal import Decimal


# ========= Inicio: Settings/Provider =============

TW_INPUT = (
    "w-full rounded-xl border border-[#eadfd3] bg-white px-3 py-2 text-sm text-[#2b1d16] "
    "placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-[#c0895e]/40 "
    "focus:border-[#c0895e]"
)

NAME_RE = re.compile(r"^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+(?:[ '\-][A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+)*$")

LETTERS_ONLY_RE = re.compile(r"[^A-Za-zÁÉÍÓÚÜÑáéíóúüñ]")


class ProviderForm(forms.ModelForm):
    class Meta:
        model = Provider
        fields = ["first_name", "last_name", "contact"]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": TW_INPUT, "placeholder": "Nombre(s)"}),
            "last_name": forms.TextInput(attrs={"class": TW_INPUT, "placeholder": "Apellidos (2)"}),
            "contact": forms.TextInput(attrs={"class": TW_INPUT, "placeholder": "Teléfono 10 dígitos o correo"}),
        }

    def _normalize_spaces(self, value: str) -> str:
        return re.sub(r"\s+", " ", (value or "").strip())

    def _letters_len(self, s: str) -> int:
        only_letters = re.sub(LETTERS_ONLY_RE, "", s or "")
        return len(only_letters)

    def clean_first_name(self):
        value = self._normalize_spaces(self.cleaned_data.get("first_name"))

        if self._letters_len(value) < 2:
            raise ValidationError("El nombre debe tener mínimo 2 letras.")

        if not NAME_RE.match(value):
            raise ValidationError("El nombre solo puede contener letras, espacios, acentos y ñ (sin números).")

        return value

    def clean_last_name(self):
        value = self._normalize_spaces(self.cleaned_data.get("last_name"))

        if not NAME_RE.match(value):
            raise ValidationError("El apellido solo puede contener letras, espacios, acentos y ñ (sin números).")

        parts = [p for p in value.split(" ") if p]
        if len(parts) < 2:
            raise ValidationError("Ingresa tus dos apellidos (ej: Pérez López).")

        for p in parts:
            if self._letters_len(p) < 2:
                raise ValidationError("Cada apellido debe tener mínimo 2 letras.")

        return value

    def clean_contact(self):
        raw = self._normalize_spaces(self.cleaned_data.get("contact"))

        if raw.isdigit():
            if len(raw) != 10:
                raise ValidationError("El teléfono debe tener exactamente 10 dígitos.")

            qs = Provider.objects.filter(contact=raw)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError("Este teléfono ya está registrado.")

            return raw

        try:
            validate_email(raw)
        except ValidationError:
            raise ValidationError("Ingresa un teléfono de 10 dígitos o un correo válido.")

        email = raw.lower()

        qs = Provider.objects.filter(contact=email)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("Este correo ya está registrado.")

        return email

# ========= Fin: Settings/Provider =============

# ========= Inicio: Quality =============

class BatchCreateForm(forms.ModelForm):
    class Meta:
        model = Batch
        fields = ["provider", "weight_kg"]
        widgets = {
            "weight_kg": forms.NumberInput(attrs={
                "class": TW_INPUT,
                "placeholder": "Peso en kg (ej: 35.50)",
                "step": "0.01",
                "min": "0"
            }),
        }

    provider = forms.ModelChoiceField(
        queryset=Provider.objects.order_by("first_name", "last_name"),
        empty_label="Selecciona un proveedor",
        widget=forms.Select(attrs={"class": TW_INPUT}),
    )

    def clean_weight_kg(self):
        w = self.cleaned_data.get("weight_kg")
        if w is None:
            return w
        if w <= Decimal("0"):
            raise ValidationError("El peso debe ser mayor a 0 (mínimo 0.01 kg).")
        if w < Decimal("0.01"):
            raise ValidationError("El peso mínimo permitido es 0.01 kg.")
        return w


class EvaluationImageForm(forms.Form):
    image = forms.ImageField()

# ========= Fin: Quality =============