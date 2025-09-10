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
    is_paid = models.BooleanField(default=False, help_text="Whether the booking has been paid")
    created_at = models.DateTimeField(auto_now_add=True)
    is_birthday = models.BooleanField(default=False, help_text="Customer confirmed birthday")
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
        Applies promotions: Happy Hours, Birthday, and Bonus Hour (+1 hour) per rules.
        """
        # Base room price (may be adjusted by Bonus Hour)
        hours_to_charge = self.hours

        # Determine promotions
        promotions_applied = []

        # Happy Hours (applies only if entire booking within window)
        hh_pct = getattr(self.bathhouse, "happy_hours_discount_percentage", Decimal("0.00")) or Decimal("0.00")
        happy_hours_applies = False
        if (getattr(self.bathhouse, "happy_hours_enabled", False) and 
            hh_pct > 0 and self.bathhouse.happy_hours_start_time and self.bathhouse.happy_hours_end_time):
            # Convert UTC start_time to local time (assuming UTC+6 for Kazakhstan)
            from django.utils import timezone
            import pytz
            
            # Convert to local timezone (UTC+6 for Kazakhstan)
            local_tz = pytz.timezone('Asia/Almaty')
            start_time_local = self.start_time.astimezone(local_tz)
            end_time_local = (self.start_time + timedelta(hours=self.hours)).astimezone(local_tz)
            
            hh_start = self.bathhouse.happy_hours_start_time
            hh_end = self.bathhouse.happy_hours_end_time
            hh_days = getattr(self.bathhouse, "happy_hours_days", []) or []
            
            print(f"DEBUG: Time comparison - Start local: {start_time_local.time()}, End local: {end_time_local.time()}, HH Start: {hh_start}, HH End: {hh_end}")
            print(f"DEBUG: Date comparison - Start date: {start_time_local.date()}, End date: {end_time_local.date()}")
            print(f"DEBUG: Day comparison - Weekday: {start_time_local.strftime('%A').upper()}, HH Days: {hh_days}")
            
            # Entire booking must be within same-day window
            # Compare by time component
            if (
                start_time_local.time() >= hh_start and
                end_time_local.time() <= hh_end and
                start_time_local.date() == end_time_local.date() and
                (not hh_days or start_time_local.strftime("%A").upper() in hh_days)
            ):
                happy_hours_applies = True
                print(f"DEBUG: Happy Hours applies! Start: {start_time_local.time()}, End: {end_time_local.time()}, HH Start: {hh_start}, HH End: {hh_end}")

        # Bonus Hour (+1) only if NOT happy hours
        bonus_hour_applies = False
        awarded_hours = 0
        print(f"DEBUG: happy_hours_applies = {happy_hours_applies}")
        if (not happy_hours_applies and getattr(self.bathhouse, "bonus_hour_enabled", False)):
            min_hours = getattr(self.bathhouse, "min_hours_for_bonus", 0) or 0
            days = getattr(self.bathhouse, "bonus_hour_days", []) or []
            award = getattr(self.bathhouse, "bonus_hours_awarded", 0) or 0
            
            # Use the same timezone conversion for weekday check
            if 'start_time_local' not in locals():
                local_tz = pytz.timezone('Asia/Almaty')
                start_time_local = self.start_time.astimezone(local_tz)
            
            weekday_str = start_time_local.strftime("%A").upper()
            print(f"DEBUG: Checking Bonus Hour - enabled: {getattr(self.bathhouse, 'bonus_hour_enabled', False)}, min_hours: {min_hours}, hours: {self.hours}, days: {days}, weekday: {weekday_str}")
            if award > 0 and self.hours >= min_hours and weekday_str in days:
                bonus_hour_applies = True
                awarded_hours = int(award)
                hours_to_charge = max(0, self.hours - awarded_hours)
                print(f"DEBUG: Bonus Hour applied! Awarded: {awarded_hours} hours, hours_to_charge: {hours_to_charge}")
        else:
            print(f"DEBUG: Bonus Hour NOT applied - happy_hours_applies: {happy_hours_applies}, bonus_enabled: {getattr(self.bathhouse, 'bonus_hour_enabled', False)}")

        # Room price based on possibly reduced chargeable hours
        room_price = self.room.price_per_hour * hours_to_charge
        
        # Add extra items price
        extra_items_price = sum(
            extra_item.item.price * extra_item.quantity
            for extra_item in self.extra_items.all()
        )
        subtotal = room_price + extra_items_price

        # Apply percentage discounts (Happy Hours is exclusive - no stacking)
        total = subtotal
        if happy_hours_applies and hh_pct > 0:
            discount = (total * hh_pct / Decimal("100")).quantize(Decimal("0.01"))
            total = (total - discount).quantize(Decimal("0.01"))
            promotions_applied.append({
                "type": "HAPPY_HOURS",
                "percent": str(hh_pct),
                "amount": str(discount),
            })

        # Birthday discount stacks with Bonus Hour, but NOT with Happy Hours (Happy Hours is exclusive)
        if (self.is_birthday and not happy_hours_applies and 
            getattr(self.bathhouse, "birthday_discount_enabled", False)):
            bday_pct = getattr(self.bathhouse, "birthday_discount_percentage", Decimal("0.00")) or Decimal("0.00")
            if bday_pct > 0:
                discount = (total * bday_pct / Decimal("100")).quantize(Decimal("0.01"))
                total = (total - discount).quantize(Decimal("0.01"))
                promotions_applied.append({
                    "type": "BIRTHDAY",
                    "percent": str(bday_pct),
                    "amount": str(discount),
                })

        if bonus_hour_applies and awarded_hours > 0:
            promotions_applied.append({
                "type": "BONUS_HOUR",
                "hours_awarded": awarded_hours,
            })

        # Temporarily annotate the instance for serializer representation
        self._promotions_applied = promotions_applied

        return total
    
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
    """Accrue bonus based on configured tiered percentages and booking final price.

    Uses bathhouse.bonus_threshold_amount with lower/higher percentages when configured.
    Falls back to bathhouse.bonus_percentage if tier percents are both zero.
    Returns created BonusTransaction or None if nothing accrued or already accrued.
    """
    bathhouse = booking.bathhouse

    # Check if bonus accrual is enabled
    if not getattr(bathhouse, "bonus_accrual_enabled", True):
        return None

    final_price = Decimal(booking.get_final_price() or 0)
    if final_price <= 0:
        return None

    threshold = getattr(bathhouse, "bonus_threshold_amount", Decimal("0.00")) or Decimal("0.00")
    lower_pct = getattr(bathhouse, "lower_bonus_percentage", Decimal("0.00")) or Decimal("0.00")
    higher_pct = getattr(bathhouse, "higher_bonus_percentage", Decimal("0.00")) or Decimal("0.00")

    # Determine applicable percent
    applicable_percent = Decimal("0.00")
    if (lower_pct > 0) or (higher_pct > 0):
        if threshold > 0 and final_price >= threshold:
            applicable_percent = Decimal(higher_pct)
        else:
            applicable_percent = Decimal(lower_pct)

    if applicable_percent <= 0:
        return None

    amount = (final_price * applicable_percent / Decimal("100")).quantize(Decimal("0.01"))

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
