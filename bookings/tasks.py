from datetime import timedelta
from celery import shared_task
from django.utils import timezone

from bookings.serializers import CONFIRMATION_TIMEOUT_MINUTES
from .models import Booking, accrue_bonus_for_booking


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


@shared_task
def accrue_finished_booking_bonuses():
    """
    Accrue bonuses for bookings that:
    - are confirmed
    - have already ended (start_time + hours <= now)
    - have not yet produced an accrual transaction
    """
    now = timezone.now()
    # Select bookings that ended already
    candidates = (
        Booking.objects.filter(confirmed=True, start_time__lte=now)
    )

    for booking in candidates:
        # Compute end time in Python to avoid DB-specific expressions
        end_time = booking.start_time + timedelta(hours=booking.hours)
        if end_time > now:
            continue
        try:
            accrue_bonus_for_booking(booking)
        except Exception:
            # Avoid breaking the whole task on a single failure
            continue
