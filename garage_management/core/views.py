from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Count
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.template.loader import render_to_string
from django.template.loader import get_template
from django.core.exceptions import ValidationError
from django.contrib.staticfiles import finders
from django.conf import settings

from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from xhtml2pdf import pisa

from datetime import timedelta, datetime
from decimal import Decimal
from io import BytesIO
import logging
import json

from .models import Customer, Vehicle, Appointment, Invoice, InvoiceItem, APPOINTMENT_STATUS_CHOICES, PAYMENT_STATUS_CHOICES
from .forms import CustomerForm, VehicleForm, AppointmentForm, InvoiceForm, InvoiceItemForm

logger = logging.getLogger(__name__)

# Dashboard View
def dashboard(request):
    """
    Dashboard-Ansicht mit Übersicht über wichtige Kennzahlen und anstehende Termine
    """
    today = timezone.now().date()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    context = {
        'total_customers': Customer.objects.count(),
        'total_vehicles': Vehicle.objects.count(),
        'total_appointments': Appointment.objects.count(),
        'appointments_today': Appointment.objects.filter(
            date_time__date=today
        ).order_by('date_time'),
        'appointments_this_week': Appointment.objects.filter(
            date_time__date__range=[week_start, week_end]
        ).count(),
        'latest_customers': Customer.objects.order_by('-id')[:5],
        'upcoming_appointments': Appointment.objects.filter(
            date_time__gte=timezone.now()
        ).order_by('date_time')[:5]
    }
    
    return render(request, 'core/dashboard.html', context)

# Kunden-Views
def customer_list(request):
    """Liste aller Kunden"""
    customers = Customer.objects.all()
    return render(request, 'core/customer_list.html', {'customers': customers})

def customer_create(request):
    """Neuen Kunden erstellen"""
    if request.method == 'POST':
        form = CustomerForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Kunde wurde erfolgreich erstellt.')
            return redirect('customer_list')
    else:
        form = CustomerForm()
    return render(request, 'core/customer_form.html', {'form': form})

def customer_detail(request, pk):
    """Kundendetails anzeigen"""
    customer = get_object_or_404(Customer, pk=pk)
    return render(request, 'core/customer_detail.html', {'customer': customer})

def customer_edit(request, pk):
    """Kundendaten bearbeiten"""
    customer = get_object_or_404(Customer, pk=pk)
    if request.method == 'POST':
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            form.save()
            messages.success(request, 'Kunde wurde erfolgreich aktualisiert.')
            return redirect('customer_detail', pk=pk)
    else:
        form = CustomerForm(instance=customer)
    return render(request, 'core/customer_form.html', {'form': form})

@require_POST
def customer_delete(request, pk):
    """Kunde löschen"""
    customer = get_object_or_404(Customer, pk=pk)
    try:
        customer.delete()
        messages.success(request, 'Kunde wurde erfolgreich gelöscht.')
    except Exception as e:
        logger.error(f"Fehler beim Löschen des Kunden {pk}: {str(e)}")
        messages.error(request, 'Fehler beim Löschen des Kunden.')
    return redirect('customer_list')

# Fahrzeug-Views
def vehicle_list(request):
    """Liste aller Fahrzeuge"""
    vehicles = Vehicle.objects.all()
    return render(request, 'core/vehicle_list.html', {'vehicles': vehicles})

def vehicle_create(request):
    """Neues Fahrzeug erstellen"""
    if request.method == 'POST':
        form = VehicleForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Fahrzeug wurde erfolgreich erstellt.')
            return redirect('vehicle_list')
    else:
        form = VehicleForm()
    return render(request, 'core/vehicle_form.html', {'form': form})

def vehicle_detail(request, pk):
    """Fahrzeugdetails anzeigen"""
    vehicle = get_object_or_404(Vehicle, pk=pk)
    return render(request, 'core/vehicle_detail.html', {'vehicle': vehicle})

def vehicle_edit(request, pk):
    """Fahrzeugdaten bearbeiten"""
    vehicle = get_object_or_404(Vehicle, pk=pk)
    if request.method == 'POST':
        form = VehicleForm(request.POST, instance=vehicle)
        if form.is_valid():
            form.save()
            messages.success(request, 'Fahrzeug wurde erfolgreich aktualisiert.')
            return redirect('vehicle_detail', pk=pk)
    else:
        form = VehicleForm(instance=vehicle)
    return render(request, 'core/vehicle_form.html', {'form': form})

@require_POST
def vehicle_delete(request, pk):
    """Fahrzeug löschen"""
    vehicle = get_object_or_404(Vehicle, pk=pk)
    try:
        vehicle.delete()
        messages.success(request, 'Fahrzeug wurde erfolgreich gelöscht.')
    except Exception as e:
        logger.error(f"Fehler beim Löschen des Fahrzeugs {pk}: {str(e)}")
        messages.error(request, 'Fehler beim Löschen des Fahrzeugs.')
    return redirect('vehicle_list')

# Termin-Views
def appointment_list(request):
    """Liste aller Termine"""
    appointments = Appointment.objects.all().select_related('customer', 'vehicle')
    
    # Filter
    status = request.GET.get('status')
    if status:
        appointments = appointments.filter(status=status)
    
    # Filter für abgeschlossene Termine ohne Rechnung
    no_invoice = request.GET.get('no_invoice')
    if no_invoice:
        appointments = appointments.filter(
            status='COMPLETED',  # Hier 'COMPLETED' statt 'completed'
            invoices__isnull=True  # Nur Termine ohne Rechnung
        )
    
    date_filter = request.GET.get('date')
    today = timezone.now().date()
    
    if date_filter == 'today':
        appointments = appointments.filter(date_time__date=today)
    elif date_filter == 'tomorrow':
        appointments = appointments.filter(date_time__date=today + timedelta(days=1))
    elif date_filter == 'this_week':
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        appointments = appointments.filter(date_time__date__range=[week_start, week_end])
    
    context = {
        'appointments': appointments,
        'status_choices': APPOINTMENT_STATUS_CHOICES,
        'current_status': status,
        'current_date': date_filter,
    }
    
    return render(request, 'core/appointment_list.html', context)

def appointment_create(request):
    """Neuen Termin erstellen"""
    if request.method == 'POST':
        form = AppointmentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Termin wurde erfolgreich erstellt.')
            return redirect('appointment_list')
    else:
        form = AppointmentForm()
    return render(request, 'core/appointment_form.html', {'form': form})

def appointment_detail(request, pk):
    """Termindetails anzeigen"""
    appointment = get_object_or_404(Appointment, pk=pk)
    return render(request, 'core/appointment_detail.html', {
        'appointment': appointment,
        'can_create_invoice': not Invoice.objects.filter(appointment=appointment).exists()
    })

def appointment_edit(request, pk):
    """Termindaten bearbeiten"""
    appointment = get_object_or_404(Appointment, pk=pk)
    if request.method == 'POST':
        form = AppointmentForm(request.POST, instance=appointment)
        if form.is_valid():
            form.save()
            messages.success(request, 'Termin wurde erfolgreich aktualisiert.')
            return redirect('appointment_list')
    else:
        form = AppointmentForm(instance=appointment)
    return render(request, 'core/appointment_form.html', {'form': form})

def appointment_pdf(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk)
    template = get_template('core/appointment_pdf.html')
    
    # Kontext für das Template
    context = {
        'appointment': appointment,
        'company_name': settings.COMPANY_NAME,
        'company_street': settings.COMPANY_STREET,
        'company_zip': settings.COMPANY_ZIP,
        'company_city': settings.COMPANY_CITY,
        'company_phone': settings.COMPANY_PHONE,
        'company_email': settings.COMPANY_EMAIL,
    }
    
    # HTML-String generieren
    html = template.render(context)
    
    # PDF erstellen
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Termin_{appointment.pk}.pdf"'
    
    # PDF aus HTML generieren
    pisa_status = pisa.CreatePDF(
        html, dest=response,
        encoding='utf-8'
    )
    
    if pisa_status.err:
        return HttpResponse('Es gab Fehler beim Erstellen des PDFs')
    
    return response

@require_POST
def appointment_delete(request, pk):
    """Termin löschen"""
    appointment = get_object_or_404(Appointment, pk=pk)
    try:
        appointment.delete()
        messages.success(request, 'Termin wurde erfolgreich gelöscht.')
    except Exception as e:
        logger.error(f"Fehler beim Löschen des Termins {pk}: {str(e)}")
        messages.error(request, 'Fehler beim Löschen des Termins.')
    return JsonResponse({'status': 'success'})

@require_POST
def appointment_update_date(request, pk):
    """Termindatum per AJAX aktualisieren"""
    try:
        appointment = get_object_or_404(Appointment, pk=pk)
        data = json.loads(request.body)
        new_date = datetime.fromisoformat(data['date'].replace('Z', '+00:00'))
        
        appointment.date_time = new_date
        appointment.save()
        
        return JsonResponse({'status': 'success'})
    except Exception as e:
        logger.error(f"Fehler beim Aktualisieren des Termindatums {pk}: {str(e)}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

def calendar_view(request):
    """Kalenderansicht mit allen Terminen"""
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        start = request.GET.get('start')
        end = request.GET.get('end')
        
        appointments = Appointment.objects.filter(
            date_time__range=[start, end]
        ).select_related('customer', 'vehicle')
        
        events = []
        for appointment in appointments:
            events.append({
                'id': appointment.pk,
                'title': f"{appointment.customer.last_name} - {appointment.vehicle.brand}",
                'start': appointment.date_time.isoformat(),
                'end': (appointment.date_time + timedelta(minutes=appointment.duration)).isoformat(),
                'status': appointment.status,
                'description': appointment.description,
                'customer': f"{appointment.customer.first_name} {appointment.customer.last_name}",
                'vehicle': f"{appointment.vehicle.brand} {appointment.vehicle.model}",
                'className': f'status-{appointment.status}'
            })
        
        return JsonResponse(events, safe=False)
    
    return render(request, 'core/calendar.html')

# Rechnungs-Views
def invoice_create(request, appointment_id):
    """Neue Rechnung erstellen"""
    appointment = get_object_or_404(Appointment, id=appointment_id)
    
    if request.method == 'POST':
        form = InvoiceForm(request.POST)
        if form.is_valid():
            invoice = form.save(commit=False)
            invoice.appointment = appointment
            try:
                invoice.save()
                messages.success(request, 'Rechnung wurde erfolgreich erstellt.')
                return redirect('invoice_edit', pk=invoice.pk)
            except ValidationError as e:
                messages.error(request, str(e))
                return render(request, 'core/invoice_form.html', {
                    'form': form,
                    'appointment': appointment
                })
    else:
        form = InvoiceForm()
    
    return render(request, 'core/invoice_form.html', {
        'form': form,
        'appointment': appointment
    })

def invoice_edit(request, pk):
    """Rechnung bearbeiten"""
    invoice = get_object_or_404(Invoice, pk=pk)
    
    if request.method == 'POST':
        form = InvoiceForm(request.POST, instance=invoice)
        if form.is_valid():
            try:
                # Alte Meldungen löschen
                storage = messages.get_messages(request)
                for _ in storage:
                    pass
                
                form.save()
                messages.success(request, 'Rechnung wurde erfolgreich aktualisiert.')
                return redirect('appointment_list')
            except ValidationError as e:
                messages.error(request, str(e))
    else:
        form = InvoiceForm(instance=invoice)
    
    return render(request, 'core/invoice_form.html', {
        'form': form,
        'invoice': invoice
    })

def invoice_list(request):
    """Liste aller Rechnungen"""
    # Filter basierend auf GET-Parametern
    status = request.GET.get('status')
    period = request.GET.get('period')
    
    invoices = Invoice.objects.all().select_related(
        'appointment__customer',
        'appointment__vehicle'
    )
    
    # Filter anwenden
    if status:
        invoices = invoices.filter(payment_status=status)
    
    if period:
        today = timezone.now().date()
        if period == 'this_month':
            invoices = invoices.filter(
                created_date__year=today.year,
                created_date__month=today.month
            )
        elif period == 'last_month':
            last_month = today.replace(day=1) - timedelta(days=1)
            invoices = invoices.filter(
                created_date__year=last_month.year,
                created_date__month=last_month.month
            )
        elif period == 'this_year':
            invoices = invoices.filter(created_date__year=today.year)
    
    # Nach Datum sortieren
    invoices = invoices.order_by('-created_date')
    
    # Statistiken berechnen
    total_amount = sum(invoice.total for invoice in invoices)
    unpaid_amount = sum(invoice.total for invoice in invoices if invoice.payment_status == 'PENDING')  # Geändert
    overdue_amount = sum(
        invoice.total 
        for invoice in invoices 
        if invoice.payment_status == 'PENDING' and invoice.due_date < timezone.now().date()  # Geändert
    )
    
    context = {
        'invoices': invoices,
        'total_amount': total_amount,
        'unpaid_amount': unpaid_amount,
        'overdue_amount': overdue_amount,
        'status_filter': status,
        'period_filter': period,
        'payment_status_choices': PAYMENT_STATUS_CHOICES,
    }
    
    return render(request, 'core/invoice_list.html', context)

def invoice_detail(request, pk):
    """Detailansicht einer Rechnung"""
    invoice = get_object_or_404(Invoice.objects.select_related(
        'appointment__customer',
        'appointment__vehicle'
    ), pk=pk)
    
    context = {
        'invoice': invoice,
        'subtotal': invoice.subtotal,
        'tax': invoice.tax,
        'total': invoice.total,
        'payment_status_choices': PAYMENT_STATUS_CHOICES,
        'is_overdue': invoice.payment_status == 'PENDING' and invoice.due_date < timezone.now().date(),
        'days_overdue': (timezone.now().date() - invoice.due_date).days if invoice.payment_status == 'PENDING' and invoice.due_date < timezone.now().date() else 0,
    }
    
    return render(request, 'core/invoice_detail.html', context)

@require_POST
def invoice_item_add(request, invoice_id):
    """Rechnungsposition hinzufügen"""
    invoice = get_object_or_404(Invoice, id=invoice_id)
    
    try:
        item = InvoiceItem.objects.create(
            invoice=invoice,
            description=request.POST.get('description'),
            quantity=Decimal(request.POST.get('quantity')),
            unit_price=Decimal(request.POST.get('unit_price')),
            vat_rate=request.POST.get('vat_rate'),
            currency=request.POST.get('currency')
        )
        
        invoice.save()  # Neuberechnung der Gesamtbeträge
        
        return JsonResponse({
            'status': 'success',
            'item': {
                'id': item.id,
                'description': item.description,
                'quantity': float(item.quantity),
                'unit_price': float(item.unit_price),
                'vat_rate': item.vat_rate,
                'currency': item.currency,
                'total': float(item.total)
            }
        })
    except Exception as e:
        logger.error(f"Fehler beim Hinzufügen der Rechnungsposition: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)

@require_POST
def invoice_item_delete(request, item_id):
    """Rechnungsposition löschen"""
    item = get_object_or_404(InvoiceItem, id=item_id)
    try:
        invoice = item.invoice
        item.delete()
        invoice.save()  # Neuberechnung der Gesamtbeträge
        return JsonResponse({'status': 'success'})
    except Exception as e:
        logger.error(f"Fehler beim Löschen der Rechnungsposition {item_id}: {str(e)}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

def invoice_pdf(request, pk):
    """PDF-Rechnung generieren"""
    invoice = get_object_or_404(Invoice.objects.select_related(
        'appointment__customer',
        'appointment__vehicle'
    ), pk=pk)
    
    template = get_template('core/invoice_pdf.html')
    context = {
        'invoice': invoice,
        'company_name': 'Ihre Autowerkstatt',  # Anpassen
        'company_street': 'Musterstraße 123',  # Anpassen
        'company_zip': '12345',                # Anpassen
        'company_city': 'Musterstadt',         # Anpassen
        'company_phone': '+49 123 456789',     # Anpassen
        'company_email': 'info@werkstatt.de'   # Anpassen
    }
    
    # HTML zu PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Rechnung_{invoice.invoice_number}.pdf"'
    
    pisa_status = pisa.CreatePDF(
        template.render(context),
        dest=response,
        encoding='utf-8'
    )
    
    if pisa_status.err:
        return HttpResponse('Fehler beim Erstellen des PDFs', status=500)
    
    return response

@require_POST
def invoice_delete(request, pk):
    """Rechnung löschen"""
    invoice = get_object_or_404(Invoice, pk=pk)
    try:
        invoice.delete()
        return JsonResponse({'status': 'success'})
    except Exception as e:
        logger.error(f"Fehler beim Löschen der Rechnung {pk}: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': 'Fehler beim Löschen der Rechnung.'
        }, status=400)

def handler404(request, exception):
    """404 Error Handler"""
    context = {
        'error_code': 404,
        'error_message': 'Die angeforderte Seite wurde nicht gefunden.'
    }
    return render(request, 'core/error.html', context, status=404)

def handler500(request):
    """500 Error Handler"""
    context = {
        'error_code': 500,
        'error_message': 'Ein interner Serverfehler ist aufgetreten.'
    }
    return render(request, 'core/error.html', context, status=500)