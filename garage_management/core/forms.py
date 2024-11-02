from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from .models import (
    Customer, 
    Vehicle, 
    Appointment, 
    Invoice, 
    InvoiceItem,
    APPOINTMENT_STATUS_CHOICES,
    VAT_CHOICES,
    CURRENCY_CHOICES
)

class BaseForm(forms.ModelForm):
    """
    Basis-Formularklasse mit gemeinsamen Funktionen und Styling
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Bootstrap-Styling für alle Formularfelder
        for field_name, field in self.fields.items():
            field.widget.attrs.update({
                'class': 'form-control',
                'placeholder': field.label
            })

class CustomerForm(BaseForm):
    """Formular für Kundenverwaltung"""
    class Meta:
        model = Customer
        fields = ['first_name', 'last_name', 'email', 'phone', 'address']
        labels = {
            'first_name': _('Vorname'),
            'last_name': _('Nachname'),
            'email': _('E-Mail'),
            'phone': _('Telefon'),
            'address': _('Adresse'),
        }
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_email(self):
        """Validierung der E-Mail-Adresse"""
        email = self.cleaned_data.get('email')
        if Customer.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise ValidationError(_('Diese E-Mail-Adresse wird bereits verwendet.'))
        return email

class VehicleForm(BaseForm):
    """Formular für Fahrzeugverwaltung"""
    class Meta:
        model = Vehicle
        fields = ['customer', 'brand', 'model', 'year', 'license_plate', 'vin']
        labels = {
            'customer': _('Kunde'),
            'brand': _('Marke'),
            'model': _('Modell'),
            'year': _('Baujahr'),
            'license_plate': _('Kennzeichen'),
            'vin': _('Fahrgestellnummer'),
        }

    def clean_license_plate(self):
        """Validierung des Kennzeichens"""
        license_plate = self.cleaned_data.get('license_plate')
        if Vehicle.objects.filter(license_plate=license_plate).exclude(pk=self.instance.pk).exists():
            raise ValidationError(_('Dieses Kennzeichen ist bereits registriert.'))
        return license_plate

    def clean_vin(self):
        """Validierung der Fahrgestellnummer"""
        vin = self.cleaned_data.get('vin')
        if Vehicle.objects.filter(vin=vin).exclude(pk=self.instance.pk).exists():
            raise ValidationError(_('Diese Fahrgestellnummer ist bereits registriert.'))
        return vin

class AppointmentForm(BaseForm):
    """Formular für Terminverwaltung"""
    class Meta:
        model = Appointment
        fields = ['customer', 'vehicle', 'date_time', 'description', 'status']
        labels = {
            'customer': _('Kunde'),
            'vehicle': _('Fahrzeug'),
            'date_time': _('Datum/Uhrzeit'),
            'description': _('Beschreibung'),
            'status': _('Status'),
        }
        widgets = {
            'date_time': forms.DateTimeInput(
                attrs={
                    'type': 'datetime-local',
                    'class': 'form-control'
                }
            ),
            'description': forms.Textarea(
                attrs={
                    'rows': 3,
                    'class': 'form-control'
                }
            ),
            'status': forms.Select(
                choices=APPOINTMENT_STATUS_CHOICES,
                attrs={'class': 'form-control'}
            )
        }

    def clean_date_time(self):
        """Validierung des Termindatums"""
        date_time = self.cleaned_data.get('date_time')
        if date_time and date_time < timezone.now():
            raise ValidationError(_('Der Termin kann nicht in der Vergangenheit liegen.'))
        return date_time

class InvoiceForm(BaseForm):
    """Formular für Rechnungsverwaltung"""
    class Meta:
        model = Invoice
        fields = ['due_date', 'notes']
        widgets = {
            'due_date': forms.DateInput(
                attrs={
                    'type': 'date',
                    'class': 'form-control'
                }
            ),
            'notes': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 3,
                    'placeholder': _('Zusätzliche Notizen zur Rechnung')
                }
            ),
        }

    def clean_due_date(self):
        """Validierung des Fälligkeitsdatums"""
        due_date = self.cleaned_data.get('due_date')
        if due_date and due_date < timezone.now().date():
            raise ValidationError(_('Das Fälligkeitsdatum kann nicht in der Vergangenheit liegen.'))
        return due_date

class InvoiceItemForm(BaseForm):
    """Formular für Rechnungspositionen"""
    class Meta:
        model = InvoiceItem
        fields = ['description', 'quantity', 'unit_price', 'vat_rate', 'currency']
        widgets = {
            'description': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': _('Beschreibung der Position')
                }
            ),
            'quantity': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'step': '0.01',
                    'min': '0.01'
                }
            ),
            'unit_price': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'step': '0.01',
                    'min': '0.01'
                }
            ),
            'vat_rate': forms.Select(
                choices=VAT_CHOICES,
                attrs={'class': 'form-control'}
            ),
            'currency': forms.Select(
                choices=CURRENCY_CHOICES,
                attrs={'class': 'form-control'}
            )
        }

    def clean(self):
        """Validierung der Gesamtposition"""
        cleaned_data = super().clean()
        quantity = cleaned_data.get('quantity')
        unit_price = cleaned_data.get('unit_price')

        if quantity and unit_price:
            if quantity <= 0:
                raise ValidationError(_('Die Menge muss größer als 0 sein.'))
            if unit_price <= 0:
                raise ValidationError(_('Der Einzelpreis muss größer als 0 sein.'))

        return cleaned_data