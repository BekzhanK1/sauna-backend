from datetime import timedelta
from celery import shared_task
from django.utils import timezone

from bookings.serializers import CONFIRMATION_TIMEOUT_MINUTES
from .models import Booking


@shared_task
def delete_unconfirmed_booking(booking_id):
    try:
        booking = Booking.objects.get(id=booking_id)
        if not booking.confirmed:
            booking.delete()
    except Booking.DoesNotExist:
        pass


@shared_task
def clean_expired_bookings():
    threshold_time = timezone.now() - timedelta(minutes=10)
    Booking.objects.filter(confirmed=False, created_at__lte=threshold_time).delete()
    print("Deleted unconfirmed bookings older than 10 minutes.")
