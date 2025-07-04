from django.contrib import admin
from .models import BathhouseItem, User, Bathhouse, Room, ExtraItem


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("username", "email", "role", "is_staff", "is_active")
    search_fields = ("username", "email")
    list_filter = ("role", "is_staff", "is_active")
    ordering = ("username",)


@admin.register(Bathhouse)
class BathhouseAdmin(admin.ModelAdmin):
    list_display = ("name", "address", "owner")
    search_fields = ("name", "address")
    list_filter = ("owner",)
    ordering = ("name",)


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = (
        "room_number",
        "bathhouse",
        "capacity",
        "price_per_hour",
        "is_available",
        "has_pool",
    )
    search_fields = ("room_number", "bathhouse__name")
    list_filter = ("bathhouse", "is_available", "has_pool")
    ordering = ("bathhouse", "room_number")


admin.site.register(ExtraItem)
admin.site.register(BathhouseItem)
