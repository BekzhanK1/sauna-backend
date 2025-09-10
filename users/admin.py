from django.contrib import admin
from .models import BathhouseItem, MenuCategory, User, Bathhouse, Room, RoomPhoto, ExtraItem


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


class RoomPhotoInline(admin.TabularInline):
    model = RoomPhoto
    extra = 1
    readonly_fields = ("image_preview",)
    
    def image_preview(self, obj):
        if obj.image:
            return f'<img src="{obj.image.url}" width="50" height="50" style="object-fit: cover;" />'
        return "No image"
    image_preview.allow_tags = True
    image_preview.short_description = "Preview"


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
    inlines = [RoomPhotoInline]


@admin.register(RoomPhoto)
class RoomPhotoAdmin(admin.ModelAdmin):
    list_display = ("room", "image_preview", "caption", "is_primary", "created_at")
    search_fields = ("room__room_number", "caption")
    list_filter = ("is_primary", "created_at", "room__bathhouse")
    ordering = ("-created_at",)
    readonly_fields = ("image_preview",)
    
    def image_preview(self, obj):
        if obj.image:
            return f'<img src="{obj.image.url}" width="100" height="100" style="object-fit: cover;" />'
        return "No image"
    image_preview.allow_tags = True
    image_preview.short_description = "Preview"


admin.site.register(ExtraItem)
admin.site.register(BathhouseItem)
admin.site.register(MenuCategory)
