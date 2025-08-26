import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sauna.settings")

app = Celery("sauna")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


# CELERY_BEAT_SCHEDULE = {
#     "clean-expired-bookings-every-1-minutes": {
#         "task": "bookings.tasks.clean_expired_bookings",
#         "schedule": crontab(minute="*/1"),
#     },
# }
# app.conf.beat_schedule = CELERY_BEAT_SCHEDULE
