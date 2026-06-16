from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from backend.app.schemas import (
    DocumentCreate,
    DocumentMetadataUpdate,
    DocumentOverviewResponse,
    DocumentResponse,
    ProcessingSummaryResponse,
    ProjectCreate,
    ProjectDetailResponse,
    ProjectListItem,
    ProjectResponse,
    ProjectUpdate,
    RetrievalResultResponse,
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
    extracted_text_path = "data/uploads/paper.extracted.txt"
    cleaned_text_path = "data/uploads/paper.cleaned.txt"
    cleaning_warnings = None
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
    assert "extracted_text_path" not in payload
    assert "cleaned_text_path" not in payload
    assert "cleaning_warnings" not in payload


def test_document_overview_response_serializes_public_overview_fields() -> None:
    payload = DocumentOverviewResponse(
        document_id=10,
        filename="paper.pdf",
        status="processed",
        page_count=12,
        word_count=4500,
        chunk_count=8,
        detected_sections=[
            {
                "section_name": "Abstract",
                "detected_heading": "Abstract",
                "confidence": 0.95,
            }
        ],
        extraction_warnings=[],
        processing_summary={
            "status": "processed",
            "message": "Document processed locally.",
            "is_complete": True,
            "requires_attention": False,
            "next_step": None,
        },
    ).model_dump()

    assert payload["document_id"] == 10
    assert payload["filename"] == "paper.pdf"
    assert payload["chunk_count"] == 8
    assert payload["detected_sections"][0]["section_name"] == "Abstract"
    assert payload["processing_summary"]["is_complete"] is True
    assert "file_path" not in payload
    assert "stored_filename" not in payload


def test_processing_summary_response_serializes_user_facing_state() -> None:
    payload = ProcessingSummaryResponse(
        status="ocr_needed",
        message="OCR may be needed.",
        is_complete=False,
        requires_attention=True,
        next_step="Use a text-based PDF.",
    ).model_dump()

    assert payload == {
        "status": "ocr_needed",
        "message": "OCR may be needed.",
        "is_complete": False,
        "requires_attention": True,
        "next_step": "Use a text-based PDF.",
    }


def test_retrieval_result_response_serializes_source_chunk_metadata() -> None:
    payload = RetrievalResultResponse(
        chunk_id=12,
        chunk_index=4,
        section_name="Methodology",
        page_start=3,
        page_end=5,
        score=0.734,
        text_preview="The methodology used local TF-IDF retrieval.",
    ).model_dump()

    assert payload == {
        "chunk_id": 12,
        "chunk_index": 4,
        "section_name": "Methodology",
        "page_start": 3,
        "page_end": 5,
        "score": 0.734,
        "text_preview": "The methodology used local TF-IDF retrieval.",
        "full_text": None,
    }
    assert "document_id" not in payload


def test_retrieval_result_response_allows_optional_full_text() -> None:
    payload = RetrievalResultResponse(
        chunk_id=12,
        chunk_index=4,
        score=0.734,
        text_preview="Preview only.",
        full_text="Preview only. Extra source context.",
    ).model_dump()

    assert payload["section_name"] is None
    assert payload["page_start"] is None
    assert payload["page_end"] is None
    assert payload["full_text"] == "Preview only. Extra source context."


def test_retrieval_result_response_rejects_negative_score() -> None:
    with pytest.raises(ValidationError):
        RetrievalResultResponse(
            chunk_id=12,
            chunk_index=4,
            score=-0.1,
            text_preview="Invalid score.",
        )
