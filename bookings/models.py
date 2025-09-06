from datetime import timedelta
from users.models import Bathhouse, Room, ExtraItem
from django.db import models
import uuid
from decimal import Decimal

CONFIRMATION_TIMEOUT_MINUTES = 10


class Booking(models.Model):
    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, unique=True
    )
    bathhouse = models.ForeignKey(
        Bathhouse, on_delete=models.CASCADE, related_name="bookings"
    )
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="bookings")
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    start_time = models.DateTimeField()
    hours = models.PositiveIntegerField(default=1)
    # TODO: For testing purposes, this should be set to False in production
    confirmed = models.BooleanField(default=True)
    sms_code = models.CharField(max_length=10, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    final_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="The final calculated price at the time of booking creation"
    )

    def calculate_final_price(self):
        """
        Calculate the final price for this booking.
        This method should be used when creating a booking to lock in the price.
        """
        # Base room price
        room_price = self.room.price_per_hour * self.hours
        
        # Add extra items price
        extra_items_price = sum(
            extra_item.item.price * extra_item.quantity
            for extra_item in self.extra_items.all()
        )
        
        return room_price + extra_items_price
    
    def get_final_price(self):
        """
        Get the final price for this booking.
        Returns the saved final_price if available, otherwise calculates it dynamically.
        """
        if self.final_price is not None:
            return self.final_price
        return self.calculate_final_price()

    def __str__(self):
        return f"Booking by {self.name} at {self.bathhouse.name} from {self.start_time} to {self.start_time + timedelta(hours=self.hours)}"


class BonusAccount(models.Model):
    bathhouse = models.ForeignKey(
        Bathhouse, on_delete=models.CASCADE, related_name="bonus_accounts"
    )
    phone = models.CharField(max_length=20)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("bathhouse", "phone")

    def __str__(self):
        return f"{self.phone} @ {self.bathhouse.name}: {self.balance}"


class BonusTransaction(models.Model):
    ACCRUAL = "accrual"
    REDEMPTION = "redemption"
    TYPE_CHOICES = (
        (ACCRUAL, "Accrual"),
        (REDEMPTION, "Redemption"),
    )

    account = models.ForeignKey(
        BonusAccount, on_delete=models.CASCADE, related_name="transactions"
    )
    booking = models.ForeignKey(
        Booking, on_delete=models.SET_NULL, null=True, blank=True, related_name="bonus_transactions"
    )
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.type} {self.amount} for {self.account.phone} ({self.account.bathhouse_id})"


def accrue_bonus_for_booking(booking: "Booking"):
    """Accrue bonus based on bathhouse percentage and booking final price."""
    percent = booking.bathhouse.bonus_percentage or Decimal("0.00")
    if Decimal(percent) <= 0:
        return None

    final_price = Decimal(booking.get_final_price() or 0)
    if final_price <= 0:
        return None

    amount = (final_price * Decimal(percent) / Decimal("100")).quantize(Decimal("0.01"))

    account, _ = BonusAccount.objects.get_or_create(
        bathhouse=booking.bathhouse, phone=booking.phone
    )

    # Prevent duplicate accruals for the same booking
    if BonusTransaction.objects.filter(booking=booking, type=BonusTransaction.ACCRUAL).exists():
        return None

    account.balance = (account.balance + amount).quantize(Decimal("0.01"))
    account.save(update_fields=["balance", "updated_at"])

    tx = BonusTransaction.objects.create(
        account=account,
        booking=booking,
        type=BonusTransaction.ACCRUAL,
        amount=amount,
    )
    return tx
