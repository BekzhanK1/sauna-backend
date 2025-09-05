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
