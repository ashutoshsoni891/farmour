"""Enqueue background jobs by name, so modules never import the jobs layer (spec section 16)."""

from functools import lru_cache
from typing import Any

from celery import Celery

from app.config import get_config


@lru_cache
def _client() -> Celery:
    return Celery("farm-producer", broker=get_config().valkey_url, backend=None)


def enqueue(task: str, *args: Any, queue: str = "default") -> None:
    _client().send_task(task, args=list(args), queue=queue)
