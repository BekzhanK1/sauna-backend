from django.conf import settings
from django.db import models
from django.contrib.auth.models import AbstractUser
from .managers import UserManager


class User(AbstractUser):
    ROLE_CHOICES = (
        ("superadmin", "Super Admin"),
        ("bath_admin", "Bathhouse Admin"),
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="bath_admin")
    objects = UserManager()

    def __str__(self):
        return f"{self.username} - {self.role}"


class Bathhouse(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    address = models.CharField(max_length=255)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="bathhouses",
        null=True,
        blank=True,
    )
    phone = models.CharField(max_length=20, blank=True)
    is_24_hours = models.BooleanField(default=False)
    start_of_work = models.TimeField(null=True, blank=True)
    end_of_work = models.TimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} - {self.owner.username if self.owner else 'No Owner'}"


class Room(models.Model):
    bathhouse = models.ForeignKey(
        Bathhouse, on_delete=models.CASCADE, related_name="rooms"
    )
    is_bathhouse = models.BooleanField(default=False)
    is_sauna = models.BooleanField(default=False)
    room_number = models.CharField(max_length=20)
    capacity = models.CharField(max_length=50, blank=True)
    price_per_hour = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    holiday_price_per_hour = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00
    )
    is_available = models.BooleanField(default=True)
    has_pool = models.BooleanField(default=False)
    has_recreation_area = models.BooleanField(default=False)
    has_steam_room = models.BooleanField(default=False)
    has_washing_area = models.BooleanField(default=False)
    heated_by_wood = models.BooleanField(default=False)
    heated_by_coal = models.BooleanField(default=False)

    def __str__(self):
        return f"{'Bathhouse' if self.is_bathhouse else 'Sauna'} {self.room_number} ({self.bathhouse.name})"

    class Meta:
        unique_together = ("bathhouse", "room_number", "is_bathhouse", "is_sauna")


class MenuCategory(models.Model):
    name = models.CharField(max_length=100)
    bathhouse = models.ForeignKey(
        Bathhouse, on_delete=models.CASCADE, related_name="menu_categories"
    )

    def __str__(self):
        return f"{self.name} ({self.bathhouse.name})"


class BathhouseItem(models.Model):
    bathhouse = models.ForeignKey(
        Bathhouse, on_delete=models.CASCADE, related_name="items"
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    is_available = models.BooleanField(default=True)
    image = models.ImageField(upload_to="bathhouse_items/", blank=True, null=True)
    category = models.ForeignKey(
        MenuCategory,
        on_delete=models.SET_NULL,
        related_name="items",
        null=True,
        blank=True,
    )

    def __str__(self):
        return f"{self.pk}: {self.name} ({self.bathhouse.name})"

    class Meta:
        unique_together = ("bathhouse", "name")


class ExtraItem(models.Model):
    item = models.ForeignKey(
        BathhouseItem, on_delete=models.CASCADE, related_name="extra_items"
    )
    quantity = models.PositiveIntegerField(default=1)
    booking = models.ForeignKey(
        "bookings.Booking", on_delete=models.CASCADE, related_name="extra_items"
    )

    def __str__(self):
        return f"{self.item.name} x ({self.quantity}) for Booking {self.booking.id}"
