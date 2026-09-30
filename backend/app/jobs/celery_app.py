"""Celery worker and beat schedule. Queues: default, messaging, ai (spec section 4)."""

import importlib
import importlib.util
import pkgutil

from celery import Celery

import app.modules
from app.config import get_config


def load_event_subscribers() -> list[str]:
    """Import every module's events.py so its @subscribe handlers are registered.

    The API process imports modules through their routers; the worker does not, so without
    this the outbox would see no subscribers.
    """
    loaded = []
    for mod in pkgutil.iter_modules(app.modules.__path__):
        name = f"app.modules.{mod.name}.events"
        if importlib.util.find_spec(name):
            importlib.import_module(name)
            loaded.append(name)
    return loaded


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
load_event_subscribers()
