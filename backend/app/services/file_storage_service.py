import shutil
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.core.config import get_settings


class PersistentFileStorageUnavailableError(RuntimeError):
    pass


def require_persistent_file_storage() -> None:
    if not get_settings().persistent_file_storage_available:
        raise PersistentFileStorageUnavailableError(
            "Persistent file storage is not configured for this environment."
        )


class FileStorageService:
    def __init__(self) -> None:
        self.upload_dir = get_settings().upload_dir.resolve()
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def save_upload(self, upload: UploadFile) -> tuple[str, int]:
        suffix = Path(upload.filename or "").suffix
        stored_name = f"{uuid.uuid4()}{suffix}"
        destination = (self.upload_dir / stored_name).resolve()
        self._require_inside_root(destination)
        try:
            with destination.open("wb") as file_obj:
                shutil.copyfileobj(upload.file, file_obj)
        except Exception:
            destination.unlink(missing_ok=True)
            raise
        return str(destination), destination.stat().st_size

    def delete_file(self, path: str) -> None:
        file_path = Path(path).resolve()
        self._require_inside_root(file_path)
        if file_path.exists() and file_path.is_file():
            file_path.unlink()

    def existing_file(self, path: str) -> Path:
        file_path = Path(path).resolve()
        self._require_inside_root(file_path)
        if not file_path.is_file():
            raise FileNotFoundError(path)
        return file_path

    def _require_inside_root(self, path: Path) -> None:
        if not path.is_relative_to(self.upload_dir):
            raise ValueError("Stored file path is outside the configured upload directory")
