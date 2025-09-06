from django.contrib import admin
from .models import Booking, BonusAccount, BonusTransaction

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'bathhouse', 'room', 'start_time', 'hours', 'confirmed')
    search_fields = ('name', 'phone', 'bathhouse__name', 'room__room_number')
    list_filter = ('bathhouse', 'room', 'confirmed', 'start_time')
    ordering = ('-start_time',)


@admin.register(BonusAccount)
class BonusAccountAdmin(admin.ModelAdmin):
    list_display = ('phone', 'bathhouse', 'balance')
    search_fields = ('phone', 'bathhouse__name')
    list_filter = ('bathhouse',)
    ordering = ('-balance',)

@admin.register(BonusTransaction)
class BonusTransactionAdmin(admin.ModelAdmin):
    list_display = ('account', 'booking', 'type', 'amount')
    search_fields = ('account__phone', 'booking__name', 'type')
    list_filter = ('type', 'booking__bathhouse', 'booking__room')
    ordering = ('-created_at',)