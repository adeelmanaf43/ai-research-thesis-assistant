from pathlib import Path

import pytest

from backend.app.services.document_storage import (
    UnsafeStoragePathError,
    build_stored_document_filename,
    ensure_path_within_directory,
    ensure_project_documents_dir,
    get_document_storage_path,
    get_project_documents_dir,
    sanitize_upload_filename,
)


def test_sanitize_upload_filename_removes_path_parts_and_unsafe_characters() -> None:
    filename = sanitize_upload_filename("../drafts/My Thesis Draft (final).PDF")

    assert filename == "My_Thesis_Draft_final.pdf"
    assert "/" not in filename
    assert "\\" not in filename


def test_sanitize_upload_filename_rejects_empty_or_unusable_values() -> None:
    with pytest.raises(ValueError, match="filename cannot be empty"):
        sanitize_upload_filename("   ")

    with pytest.raises(ValueError, match="usable file name"):
        sanitize_upload_filename("../..")


def test_build_stored_document_filename_adds_unique_safe_prefix() -> None:
    filename = build_stored_document_filename("Research Plan!.pdf", unique_token="doc 123")

    assert filename == "doc_123_Research_Plan.pdf"


def test_get_project_documents_dir_uses_project_scoped_structure(workspace_tmp_path: Path) -> None:
    upload_dir = workspace_tmp_path / "uploads"

    documents_dir = get_project_documents_dir(upload_dir, project_id=42)

    assert documents_dir == (upload_dir / "projects" / "42" / "documents").resolve(strict=False)


def test_ensure_project_documents_dir_creates_directory(workspace_tmp_path: Path) -> None:
    upload_dir = workspace_tmp_path / "uploads"

    documents_dir = ensure_project_documents_dir(upload_dir, project_id=7)

    assert documents_dir.exists()
    assert documents_dir.is_dir()


def test_get_document_storage_path_stays_inside_project_documents_dir(workspace_tmp_path: Path) -> None:
    upload_dir = workspace_tmp_path / "uploads"

    storage_path = get_document_storage_path(upload_dir, project_id=3, stored_filename="../../paper.pdf")

    assert storage_path == (upload_dir / "projects" / "3" / "documents" / "paper.pdf").resolve(strict=False)


def test_storage_helpers_reject_invalid_project_id(workspace_tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="positive integer"):
        get_project_documents_dir(workspace_tmp_path / "uploads", project_id=0)

    with pytest.raises(ValueError, match="positive integer"):
        get_project_documents_dir(workspace_tmp_path / "uploads", project_id=-1)


def test_ensure_path_within_directory_rejects_path_traversal(workspace_tmp_path: Path) -> None:
    upload_dir = workspace_tmp_path / "uploads"
    outside_path = workspace_tmp_path / "outside.pdf"

    with pytest.raises(UnsafeStoragePathError):
        ensure_path_within_directory(outside_path, upload_dir)
