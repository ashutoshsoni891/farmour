from typing import Protocol


class ObjectStorage(Protocol):
    """S3-compatible private object storage. Files are served only via short-lived signed URLs."""

    async def presign_put(
        self, key: str, content_type: str, max_bytes: int, expires_s: int
    ) -> str: ...

    async def presign_get(self, key: str, expires_s: int) -> str: ...

    async def ping(self) -> bool: ...
