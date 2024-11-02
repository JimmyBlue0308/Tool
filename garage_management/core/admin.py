from django.contrib import admin
from .models import Customer, Vehicle, Appointment

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'email', 'phone')
    search_fields = ('first_name', 'last_name', 'email')

@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ('brand', 'model', 'license_plate', 'customer')
    search_fields = ('brand', 'model', 'license_plate')

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('customer', 'vehicle', 'date_time', 'status')
    list_filter = ('status', 'date_time')
    search_fields = ('customer__first_name', 'customer__last_name', 'vehicle__license_plate')