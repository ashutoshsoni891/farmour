class FakeStorage:
    def __init__(self) -> None:
        self.presigned: list[tuple[str, str]] = []

    async def presign_put(self, key: str, content_type: str, max_bytes: int, expires_s: int) -> str:
        self.presigned.append(("put", key))
        return f"https://storage.test/{key}?op=put&exp={expires_s}"

    async def presign_get(self, key: str, expires_s: int) -> str:
        self.presigned.append(("get", key))
        return f"https://storage.test/{key}?op=get&exp={expires_s}"

    async def ping(self) -> bool:
        return True
