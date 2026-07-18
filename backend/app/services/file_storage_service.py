import shutil
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.core.config import get_settings


class FileStorageService:
    def __init__(self) -> None:
        self.upload_dir = get_settings().upload_dir
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def save_upload(self, upload: UploadFile) -> tuple[str, int]:
        suffix = Path(upload.filename or "").suffix
        stored_name = f"{uuid.uuid4()}{suffix}"
        destination = self.upload_dir / stored_name
        with destination.open("wb") as file_obj:
            shutil.copyfileobj(upload.file, file_obj)
        return str(destination), destination.stat().st_size

    def delete_file(self, path: str) -> None:
        file_path = Path(path)
        if file_path.exists() and file_path.is_file():
            file_path.unlink()

