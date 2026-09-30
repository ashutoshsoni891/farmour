"""S3 API implementation (SeaweedFS locally; R2, B2 or AWS S3 by changing the endpoint)."""

import asyncio
from typing import Any

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import BotoCoreError, ClientError


class S3Storage:
    def __init__(self, endpoint: str, access_key: str, secret_key: str, bucket: str) -> None:
        self._bucket = bucket
        self._client: Any = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=BotoConfig(signature_version="s3v4", s3={"addressing_style": "path"}),
        )

    async def presign_put(self, key: str, content_type: str, max_bytes: int, expires_s: int) -> str:
        params = {"Bucket": self._bucket, "Key": key, "ContentType": content_type}
        url: str = await asyncio.to_thread(
            self._client.generate_presigned_url, "put_object", Params=params, ExpiresIn=expires_s
        )
        return url

    async def presign_get(self, key: str, expires_s: int) -> str:
        params = {"Bucket": self._bucket, "Key": key}
        url: str = await asyncio.to_thread(
            self._client.generate_presigned_url, "get_object", Params=params, ExpiresIn=expires_s
        )
        return url

    async def ping(self) -> bool:
        try:
            await asyncio.to_thread(self._client.head_bucket, Bucket=self._bucket)
        except (BotoCoreError, ClientError):
            return False
        return True
