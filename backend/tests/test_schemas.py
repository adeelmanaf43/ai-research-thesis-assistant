from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from backend.app.schemas import (
    DocumentCreate,
    DocumentMetadataUpdate,
    DocumentResponse,
    ProjectCreate,
    ProjectDetailResponse,
    ProjectListItem,
    ProjectResponse,
    ProjectUpdate,
)


class ProjectLike:
    id = 1
    user_id = None
    name = "Thesis research"
    description = "Local MVP project"
    created_at = datetime(2026, 1, 1, tzinfo=UTC)
    updated_at = datetime(2026, 1, 2, tzinfo=UTC)


class DocumentLike:
    id = 10
    project_id = 1
    original_filename = "paper.pdf"
    stored_filename = "internal-uuid.pdf"
    file_path = "data/uploads/internal-uuid.pdf"
    mime_type = "application/pdf"
    file_size_bytes = 2048
    page_count = 12
    word_count = 4500
    status = "created"
    extraction_error = None
    uploaded_at = datetime(2026, 1, 3, tzinfo=UTC)


def test_project_create_validates_name() -> None:
    schema = ProjectCreate(name="  Literature review  ", description="Chapter two")

    assert schema.name == "Literature review"
    assert schema.description == "Chapter two"


def test_project_create_rejects_empty_name() -> None:
    with pytest.raises(ValidationError):
        ProjectCreate(name="")


def test_project_create_rejects_whitespace_name() -> None:
    with pytest.raises(ValidationError):
        ProjectCreate(name="   ")


def test_project_response_serializes_from_attributes() -> None:
    payload = ProjectResponse.model_validate(ProjectLike()).model_dump()

    assert payload["id"] == 1
    assert payload["user_id"] is None
    assert payload["name"] == "Thesis research"
    assert payload["created_at"] == datetime(2026, 1, 1, tzinfo=UTC)


def test_project_update_allows_partial_updates() -> None:
    schema = ProjectUpdate(description="Updated description")

    assert schema.name is None
    assert schema.description == "Updated description"


def test_project_update_strips_name_and_rejects_blank_name() -> None:
    assert ProjectUpdate(name="  Updated title  ").name == "Updated title"
    with pytest.raises(ValidationError):
        ProjectUpdate(name="   ")


def test_project_list_and_detail_schemas_serialize_from_attributes() -> None:
    list_payload = ProjectListItem.model_validate(ProjectLike()).model_dump()
    detail_payload = ProjectDetailResponse.model_validate(ProjectLike()).model_dump()

    assert list_payload["name"] == "Thesis research"
    assert detail_payload["description"] == "Local MVP project"


def test_document_create_validates_public_upload_metadata() -> None:
    schema = DocumentCreate(
        project_id=1,
        original_filename="paper.pdf",
        mime_type="application/pdf",
        file_size_bytes=2048,
    )

    assert schema.project_id == 1
    assert schema.original_filename == "paper.pdf"


def test_document_create_rejects_negative_file_size() -> None:
    with pytest.raises(ValidationError):
        DocumentCreate(project_id=1, original_filename="paper.pdf", file_size_bytes=-1)


def test_document_metadata_update_rejects_negative_counts() -> None:
    with pytest.raises(ValidationError):
        DocumentMetadataUpdate(page_count=-1)


def test_document_metadata_update_accepts_extraction_error() -> None:
    schema = DocumentMetadataUpdate(
        page_count=None,
        word_count=None,
        status="extraction_failed",
        extraction_error="Could not extract text",
    )

    assert schema.extraction_error == "Could not extract text"


def test_document_response_excludes_internal_storage_fields() -> None:
    payload = DocumentResponse.model_validate(DocumentLike()).model_dump()

    assert payload["id"] == 10
    assert payload["project_id"] == 1
    assert payload["original_filename"] == "paper.pdf"
    assert payload["status"] == "created"
    assert payload["extraction_error"] is None
    assert "file_path" not in payload
    assert "stored_filename" not in payload
