from datetime import timedelta
from users.models import Bathhouse, Room, ExtraItem
from django.db import models

CONFIRMATION_TIMEOUT_MINUTES = 10


class Booking(models.Model):
    bathhouse = models.ForeignKey(
        Bathhouse, on_delete=models.CASCADE, related_name="bookings"
    )
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="bookings")
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    start_time = models.DateTimeField()
    hours = models.PositiveIntegerField(default=1)
    confirmed = models.BooleanField(default=False)
    sms_code = models.CharField(max_length=10, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Booking by {self.name} at {self.bathhouse.name} from {self.start_time} to {self.start_time + timedelta(hours=self.hours)}"
