import uuid
from pathlib import Path

import aiofiles

from app.core.config import settings


class StorageService:
    def __init__(self) -> None:
        self.base_path = Path(settings.storage_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    async def save(self, file_bytes: bytes, subdir: str, filename: str) -> Path:
        target_dir = self.base_path / subdir
        target_dir.mkdir(parents=True, exist_ok=True)
        file_path = target_dir / filename
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(file_bytes)
        return file_path

    async def read(self, relative_path: str) -> bytes:
        file_path = self.base_path / relative_path
        async with aiofiles.open(file_path, "rb") as f:
            return await f.read()

    def relative_path(self, full_path: Path) -> str:
        return str(full_path.relative_to(self.base_path))
