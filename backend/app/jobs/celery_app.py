"""Celery worker and beat schedule. Queues: default, messaging, ai (spec section 4)."""

from celery import Celery

from app.config import get_config

cfg = get_config()
celery = Celery("farm", broker=cfg.valkey_url, backend=None, include=["app.jobs.outbox"])
celery.conf.update(
    task_default_queue="default",
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    timezone="Asia/Kolkata",
    enable_utc=True,
    beat_schedule={
        "deliver-outbox": {"task": "outbox.deliver", "schedule": 5.0},
    },
)
