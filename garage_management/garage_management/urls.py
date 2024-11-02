from django.contrib import admin
from django.urls import path, include
from core import views



# URL-Muster für die Hauptnavigation
main_patterns = [
    path('', views.dashboard, name='dashboard'),
    path('admin/', admin.site.urls),
]

# URL-Muster für Kundenverwaltung
customer_patterns = [
    path('customers/', views.customer_list, name='customer_list'),
    path('customers/create/', views.customer_create, name='customer_create'),
    path('customers/<int:pk>/', views.customer_detail, name='customer_detail'),
    path('customers/<int:pk>/edit/', views.customer_edit, name='customer_edit'),
    path('customers/<int:pk>/delete/', views.customer_delete, name='customer_delete'),
]

# URL-Muster für Fahrzeugverwaltung
vehicle_patterns = [
    path('vehicles/', views.vehicle_list, name='vehicle_list'),
    path('vehicles/create/', views.vehicle_create, name='vehicle_create'),
    path('vehicles/<int:pk>/', views.vehicle_detail, name='vehicle_detail'),
    path('vehicles/<int:pk>/edit/', views.vehicle_edit, name='vehicle_edit'),
    path('vehicles/<int:pk>/delete/', views.vehicle_delete, name='vehicle_delete'),
]

# URL-Muster für Terminverwaltung
appointment_patterns = [
    path('appointments/', views.appointment_list, name='appointment_list'),
    path('appointments/create/', views.appointment_create, name='appointment_create'),
    path('appointments/<int:pk>/', views.appointment_detail, name='appointment_detail'),
    path('appointments/<int:pk>/edit/', views.appointment_edit, name='appointment_edit'),
    path('appointments/<int:pk>/delete/', views.appointment_delete, name='appointment_delete'),
    path('appointments/<int:pk>/update-date/', views.appointment_update_date, name='appointment_update_date'),
    path('appointments/<int:pk>/pdf/', views.appointment_pdf, name='appointment_pdf'),
]

# URL-Muster für Kalenderfunktionen
calendar_patterns = [
    path('calendar/', views.calendar_view, name='calendar'),
    path('api/calendar-events/', views.calendar_view, name='calendar_events'),
]

# URL-Muster für Rechnungsverwaltung
invoice_patterns = [
    path('invoices/', views.invoice_list, name='invoice_list'),
    path('invoices/create/<int:appointment_id>/', views.invoice_create, name='invoice_create'),
    path('invoices/<int:pk>/', views.invoice_detail, name='invoice_detail'),
    path('invoices/<int:pk>/edit/', views.invoice_edit, name='invoice_edit'),
    path('invoices/<int:invoice_id>/items/add/', views.invoice_item_add, name='invoice_item_add'),
    path('invoices/items/<int:item_id>/delete/', views.invoice_item_delete, name='invoice_item_delete'),
    path('invoices/<int:pk>/pdf/', views.invoice_pdf, name='invoice_pdf'),
    path('invoices/<int:pk>/delete/', views.invoice_delete, name='invoice_delete'),
]

# Zusammenführen aller URL-Muster
urlpatterns = (
    main_patterns +
    customer_patterns +
    vehicle_patterns +
    appointment_patterns +
    calendar_patterns +
    invoice_patterns
)

# Debug-Toolbar URLs (nur in Entwicklungsumgebung)
from django.conf import settings
if settings.DEBUG:
    import debug_toolbar
    urlpatterns += [
        path('__debug__/', include(debug_toolbar.urls)),
    ]

# Handler für Fehlerseiten
handler404 = 'core.views.handler404'
handler500 = 'core.views.handler500'