from __future__ import annotations

"""
Celery app for the Proactive Engine.
"""

from celery import Celery
from celery.schedules import crontab

from config import settings

celery_app = Celery(
    "umnick_engine",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
)

# Beat schedule for watchers only
celery_app.conf.beat_schedule = {
    "check-watchers-every-minute": {
        "task": "tasks.check_due_watchers",
        "schedule": 60.0,
    },
}
