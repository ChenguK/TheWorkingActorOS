from __future__ import annotations

from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI, UploadFile
from fastapi.responses import FileResponse
from fastapi.testclient import TestClient

from app.services.asset_service import AssetService
from app.services.file_storage_service import FileStorageService
from app.services.resume_pdf_service import ResumePdfService


def upload(filename: str = "headshot.jpg", content: bytes = b"portfolio asset") -> UploadFile:
    return UploadFile(filename=filename, file=BytesIO(content))


def storage_settings(root: Path):
    return SimpleNamespace(upload_dir=root)


def asset_service(root: Path) -> tuple[AssetService, MagicMock, MagicMock]:
    db = MagicMock()
    service = AssetService.__new__(AssetService)
    service.db = db
    service.repo = MagicMock()
    with patch(
        "app.services.file_storage_service.get_settings",
        return_value=storage_settings(root),
    ):
        service.storage = FileStorageService()
    service.repo.add.side_effect = lambda asset: asset
    return service, db, service.repo


def create_asset(service: AssetService, source: UploadFile | None = None):
    with (
        patch("app.services.asset_service.WorkflowConnectorService") as connector,
        patch("app.services.asset_service.ActorWorkEventService") as actor_work,
    ):
        asset = service.create(
            actor_profile_id=uuid4(),
            asset_name="Portfolio Headshot",
            asset_type="Headshot",
            description="Sanitized test asset",
            tags=["theatrical"],
            archetype_names=["Authority"],
            upload=source or upload(),
        )
    connector.return_value.after_asset_created.assert_called_once()
    actor_work.return_value.material_uploaded.assert_called_once()
    return asset


def test_successful_upload_persists_file_metadata_and_download_bytes_inside_root(tmp_path):
    root = tmp_path / "uploads"
    service, db, _repo = asset_service(root)

    asset = create_asset(service)
    stored = Path(asset.local_file_path)

    assert stored.exists()
    assert stored.read_bytes() == b"portfolio asset"
    assert stored.resolve().is_relative_to(root.resolve())
    assert asset.original_filename == "headshot.jpg"
    assert asset.mime_type is None
    assert asset.file_size_bytes == len(b"portfolio asset")
    assert db.flush.call_count == 1
    assert db.commit.call_count == 1

    app = FastAPI()

    @app.get("/download")
    def download():
        return FileResponse(
            asset.local_file_path,
            media_type=asset.mime_type,
            filename=asset.original_filename,
        )

    response = TestClient(app).get("/download")
    assert response.status_code == 200
    assert response.content == b"portfolio asset"


def test_database_failure_after_file_write_leaves_orphaned_file(tmp_path):
    root = tmp_path / "uploads"
    service, db, repo = asset_service(root)
    repo.add.side_effect = RuntimeError("database insert failed")

    with pytest.raises(RuntimeError, match="database insert failed"):
        create_asset(service)

    assert [path.read_bytes() for path in root.iterdir()] == [b"portfolio asset"]
    db.commit.assert_not_called()


def test_filesystem_write_failure_creates_no_database_row(tmp_path):
    service, db, repo = asset_service(tmp_path / "uploads")
    service.storage.save_upload = MagicMock(side_effect=OSError("disk unavailable"))

    with pytest.raises(OSError, match="disk unavailable"):
        create_asset(service)

    repo.add.assert_not_called()
    db.flush.assert_not_called()
    db.commit.assert_not_called()


def test_delete_commits_metadata_before_removing_existing_file(tmp_path):
    root = tmp_path / "uploads"
    service, db, repo = asset_service(root)
    stored = root / "asset.jpg"
    stored.write_bytes(b"asset")
    asset = SimpleNamespace(local_file_path=str(stored))
    repo.get.return_value = asset

    service.delete(uuid4())

    repo.delete.assert_called_once_with(asset)
    db.commit.assert_called_once()
    assert not stored.exists()


def test_delete_succeeds_when_database_record_points_to_missing_file(tmp_path):
    service, db, repo = asset_service(tmp_path / "uploads")
    asset = SimpleNamespace(local_file_path=str(tmp_path / "uploads" / "missing.jpg"))
    repo.get.return_value = asset

    service.delete(uuid4())

    repo.delete.assert_called_once_with(asset)
    db.commit.assert_called_once()


def test_file_delete_failure_occurs_after_database_commit(tmp_path):
    service, db, repo = asset_service(tmp_path / "uploads")
    repo.get.return_value = SimpleNamespace(local_file_path=str(tmp_path / "asset.jpg"))
    service.storage.delete_file = MagicMock(side_effect=OSError("delete failed"))

    with pytest.raises(OSError, match="delete failed"):
        service.delete(uuid4())

    db.commit.assert_called_once()


def test_missing_file_response_is_an_unhandled_server_error(tmp_path):
    app = FastAPI()

    @app.get("/missing")
    def missing():
        return FileResponse(tmp_path / "missing.pdf")

    response = TestClient(app, raise_server_exceptions=False).get("/missing")
    assert response.status_code == 500


def test_restart_with_same_root_preserves_bytes_but_empty_replacement_root_does_not(tmp_path):
    original_root = tmp_path / "instance-one"
    with patch(
        "app.services.file_storage_service.get_settings",
        return_value=storage_settings(original_root),
    ):
        first = FileStorageService()
        stored_path, _size = first.save_upload(upload())
        restarted = FileStorageService()

    assert Path(stored_path).exists()
    assert Path(stored_path).parent == restarted.upload_dir

    replacement_root = tmp_path / "instance-two"
    with patch(
        "app.services.file_storage_service.get_settings",
        return_value=storage_settings(replacement_root),
    ):
        replacement = FileStorageService()

    assert replacement.upload_dir.exists()
    assert not (replacement.upload_dir / Path(stored_path).name).exists()


def test_storage_initialization_creates_directories_and_delete_accepts_outside_paths(tmp_path):
    root = tmp_path / "uploads"
    outside = tmp_path / "outside.txt"
    outside.write_text("outside")

    with patch(
        "app.services.file_storage_service.get_settings",
        return_value=storage_settings(root),
    ):
        storage = FileStorageService()
        storage.delete_file(str(outside))

    assert root.is_dir()
    assert not outside.exists()


def test_generated_resume_files_are_persistent_assets_under_upload_root(tmp_path):
    root = tmp_path / "uploads"
    db = MagicMock()
    actor_id = uuid4()
    actor = SimpleNamespace(
        id=actor_id,
        name="Demo Actor",
        union_status="SAG-AFTRA",
        sag_status="SAG-AFTRA",
        representations=[],
        skills=["Stage combat"],
        accents=[],
    )
    db.get.return_value = actor
    db.scalars.return_value = []

    with (
        patch(
            "app.services.file_storage_service.get_settings",
            return_value=storage_settings(root),
        ),
        patch(
            "app.services.resume_pdf_service.get_settings",
            return_value=storage_settings(root),
        ),
    ):
        service = ResumePdfService(db)
        asset = service.regenerate_for_actor(actor_id)

    pdf = Path(asset.local_file_path)
    docx_assets = [
        call.args[0]
        for call in db.add.call_args_list
        if call.args[0].mime_type
        == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ]
    assert pdf.exists()
    assert pdf.parent == root / "generated_resumes"
    assert docx_assets and Path(docx_assets[0].local_file_path).exists()
    assert db.add.call_count == 2
