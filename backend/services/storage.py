"""
Storage abstraction for uploaded documents (and later, generated reports/exports).

`path` throughout is a backend-relative key, e.g. "<submission_id>/deck/<uuid>_<filename>",
never an absolute filesystem path — so a LocalStorageBackend key and a future
BoxStorageBackend key (Checkpoint 5) mean the same thing to callers.
"""
from abc import ABC, abstractmethod
from functools import lru_cache
from pathlib import Path

from core.config import get_settings


class StorageBackend(ABC):
    @abstractmethod
    async def save(self, path: str, contents: bytes) -> str:
        """Writes `contents` under `path`, returning the key to store (usually `path` itself)."""

    @abstractmethod
    async def open(self, path: str) -> bytes:
        """Reads back what `save` wrote. Raises FileNotFoundError if `path` doesn't exist."""

    @abstractmethod
    async def delete(self, path: str) -> None:
        """Removes `path`. A no-op (not an error) if it doesn't exist."""

    @abstractmethod
    async def list(self, prefix: str) -> list[str]:
        """Lists all keys starting with `prefix`."""


class LocalStorageBackend(StorageBackend):
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, path: str) -> Path:
        # Reject absolute paths / ".." segments so `path` can't escape `root`.
        resolved = (self.root / path).resolve()
        if resolved != self.root and self.root not in resolved.parents:
            raise ValueError(f"Storage path escapes root: {path!r}")
        return resolved

    async def save(self, path: str, contents: bytes) -> str:
        target = self._resolve(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(contents)
        return path

    async def open(self, path: str) -> bytes:
        target = self._resolve(path)
        if not target.is_file():
            raise FileNotFoundError(path)
        return target.read_bytes()

    async def delete(self, path: str) -> None:
        target = self._resolve(path)
        target.unlink(missing_ok=True)

    async def list(self, prefix: str) -> list[str]:
        base = self._resolve(prefix)
        search_root = base if base.is_dir() else base.parent
        if not search_root.is_dir():
            return []
        return [
            str(p.relative_to(self.root))
            for p in search_root.rglob("*")
            if p.is_file() and str(p.relative_to(self.root)).startswith(prefix)
        ]


@lru_cache()
def get_storage_backend() -> StorageBackend:
    settings = get_settings()
    if settings.storage_backend == "local":
        return LocalStorageBackend(Path(settings.upload_dir))
    if settings.storage_backend == "box":
        # Checkpoint 5. Fails loudly now rather than silently falling back, since a
        # misconfigured STORAGE_BACKEND should never pass for "it's saving locally".
        raise NotImplementedError("STORAGE_BACKEND=box isn't implemented until Checkpoint 5.")
    raise ValueError(f"Unknown STORAGE_BACKEND: {settings.storage_backend!r}")
