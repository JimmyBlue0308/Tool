from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal, ROUND_HALF_UP
from django.core.exceptions import ValidationError

# Globale Konstanten
PAYMENT_STATUS_CHOICES = [
    ('PENDING', 'Unbezahlt'),
    ('PAID', 'Bezahlt'),
    ('CANCELLED', 'Storniert'),
]

APPOINTMENT_STATUS_CHOICES = [
    ('SCHEDULED', 'Geplant'),
    ('IN_PROGRESS', 'In Bearbeitung'),
    ('COMPLETED', 'Abgeschlossen'),
    ('CANCELLED', 'Storniert'),
]

CURRENCY_CHOICES = [
    ('EUR', '€'),
    ('CHF', 'CHF'),
]

VAT_CHOICES = [
    ('19.0', '19% (DE Standard)'),
    ('7.0', '7% (DE Reduziert)'),
    ('20.0', '20% (AT Standard)'),
    ('10.0', '10% (AT Reduziert)'),
    ('7.7', '7.7% (CH Standard)'),
    ('2.5', '2.5% (CH Reduziert)'),
    ('0.0', 'Keine MwSt.'),
]

class Customer(models.Model):
    """Kundenmodell für die Verwaltung von Kundendaten"""
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20)
    address = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    class Meta:
        ordering = ['last_name', 'first_name']
        verbose_name = 'Kunde'
        verbose_name_plural = 'Kunden'

class Vehicle(models.Model):
    """Fahrzeugmodell für die Verwaltung von Fahrzeugdaten"""
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='vehicles')
    brand = models.CharField(max_length=50)
    model = models.CharField(max_length=50)
    year = models.IntegerField()
    license_plate = models.CharField(max_length=20, unique=True)
    vin = models.CharField(max_length=17, unique=True, verbose_name="VIN")
    
    def __str__(self):
        return f"{self.brand} {self.model} ({self.license_plate})"

    class Meta:
        ordering = ['brand', 'model']
        verbose_name = 'Fahrzeug'
        verbose_name_plural = 'Fahrzeuge'

class Appointment(models.Model):
    """Termin-Model für die Verwaltung von Werkstattterminen"""
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE)
    date_time = models.DateTimeField()
    duration = models.IntegerField(default=60)  # Dauer in Minuten
    description = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=APPOINTMENT_STATUS_CHOICES,
        default='SCHEDULED'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Termin: {self.customer.last_name} - {self.date_time.strftime('%d.%m.%Y %H:%M')}"

    class Meta:
        ordering = ['-date_time']

class Invoice(models.Model):
    """Rechnungsmodell für die Verwaltung von Kundenrechnungen"""
    appointment = models.ForeignKey(
        'Appointment', 
        on_delete=models.CASCADE, 
        related_name='invoices'
    )
    invoice_number = models.CharField(max_length=50, unique=True)
    created_date = models.DateTimeField(default=timezone.now)
    due_date = models.DateField()
    payment_status = models.CharField(
        max_length=20, 
        choices=PAYMENT_STATUS_CHOICES, 
        default='PENDING'
    )
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    notes = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            self.generate_invoice_number()
        
        if self.pk:  # Wenn die Rechnung bereits existiert
            self.validate_invoice()
            self.calculate_totals()
        
        super().save(*args, **kwargs)

    def generate_invoice_number(self):
        """Generiert eine eindeutige Rechnungsnummer"""
        last_invoice = Invoice.objects.order_by('-created_date').first()
        if last_invoice:
            last_number = int(last_invoice.invoice_number.split('/')[-1])
            new_number = last_number + 1
        else:
            new_number = 1
        
        self.invoice_number = f"{timezone.now().strftime('%Y/%m')}/{new_number:04d}"

    def validate_invoice(self):
        """Validiert die Rechnung vor dem Speichern"""
        if not self.items.exists():
            raise ValidationError("Eine Rechnung muss mindestens eine Position enthalten.")
        
        if self.total <= 0:
            raise ValidationError("Der Rechnungsbetrag muss größer als 0 sein.")

    def calculate_totals(self):
        """Berechnet die Gesamtbeträge der Rechnung"""
        self.subtotal = sum(item.total for item in self.items.all())
        self.tax = sum(item.vat_amount for item in self.items.all())
        self.total = self.subtotal + self.tax

    def __str__(self):
        return f"Rechnung {self.invoice_number}"

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            self.generate_invoice_number()

        self.calculate_totals()
        
        # Validierung nur durchführen, wenn die Rechnung finalisiert wird
        if self.payment_status != 'PENDING':
            self.validate_invoice()
        
        super().save(*args, **kwargs)

    def generate_invoice_number(self):
        """Generiert eine eindeutige Rechnungsnummer"""
        last_invoice = Invoice.objects.order_by('-created_date').first()
        if last_invoice:
            last_number = int(last_invoice.invoice_number.split('/')[-1])
            new_number = last_number + 1
        else:
            new_number = 1
        
        self.invoice_number = f"{timezone.now().strftime('%Y/%m')}/{new_number:04d}"

    def validate_invoice(self):
        """Validiert die Rechnung vor dem Speichern"""
        if not self.items.exists():
            raise ValidationError("Eine Rechnung muss mindestens eine Position enthalten.")
        
        if self.total <= 0:
            raise ValidationError("Der Rechnungsbetrag muss größer als 0 sein.")

    def calculate_totals(self):
        """Berechnet die Gesamtbeträge der Rechnung"""
        items = self.items.all()
        if items:  # Nur berechnen wenn Positionen existieren
            self.subtotal = sum(item.total for item in items)
            self.tax = sum(item.vat_amount for item in items)
            self.total = self.subtotal + self.tax

    def __str__(self):
        return f"Rechnung {self.invoice_number}"

    class Meta:
        ordering = ['-created_date']
        verbose_name = 'Rechnung'
        verbose_name_plural = 'Rechnungen'

class InvoiceItem(models.Model):
    """Rechnungspositionsmodell für einzelne Positionen einer Rechnung"""
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    description = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    vat_rate = models.CharField(max_length=4, choices=VAT_CHOICES, default='19.0')
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='EUR')

    def round_chf(self, amount):
        """Rundet den Betrag auf 0.05 CHF"""
        if self.currency == 'CHF':
            return Decimal(round(float(amount) * 20) / 20).quantize(
                Decimal('0.05'), 
                rounding=ROUND_HALF_UP
            )
        return amount

    @property
    def total(self):
        """Berechnet den Gesamtbetrag der Position"""
        amount = self.quantity * self.unit_price
        return self.round_chf(amount)

    @property
    def vat_amount(self):
        """Berechnet den Mehrwertsteuerbetrag der Position"""
        amount = self.total * (Decimal(self.vat_rate) / Decimal('100'))
        return self.round_chf(amount)

    def __str__(self):
        return f"{self.description} ({self.quantity}x)"

    class Meta:
        ordering = ['id']
        verbose_name = 'Rechnungsposition'
        verbose_name_plural = 'Rechnungspositionen'