from django.contrib import admin
from .models import Booking

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'bathhouse', 'room', 'start_time', 'hours', 'confirmed')
    search_fields = ('name', 'phone', 'bathhouse__name', 'room__room_number')
    list_filter = ('bathhouse', 'room', 'confirmed', 'start_time')
    ordering = ('-start_time',)