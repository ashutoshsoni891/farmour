"""Private object storage (S3 API)."""

from app.adapters.registry import Registry
from app.adapters.storage.base import ObjectStorage
from app.adapters.storage.fake import FakeStorage
from app.config import get_config

registry: Registry[ObjectStorage] = Registry("storage")
registry.register("fake", FakeStorage)


def _s3() -> ObjectStorage:
    from app.adapters.storage.s3 import S3Storage

    cfg = get_config()
    return S3Storage(
        endpoint=cfg.s3_endpoint,
        access_key=cfg.s3_access_key.get_secret_value(),
        secret_key=cfg.s3_secret_key.get_secret_value(),
        bucket=cfg.s3_bucket,
    )


registry.register("s3", _s3)


def get_storage() -> ObjectStorage:
    return registry.get(get_config().storage_adapter)


__all__ = ["ObjectStorage", "get_storage", "registry"]
