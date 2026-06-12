from pathlib import Path

import pytest

from backend.app.core.config import Settings
from backend.app.core.database import create_database_engine, get_session_factory, init_database
from backend.app.schemas.document import DocumentCreate
from backend.app.schemas.project import ProjectCreate
from backend.app.services.document_service import (
    MIN_EXTRACTED_WORDS_FOR_TEXT,
    count_words,
    create_document_record,
    is_ocr_likely_needed,
    list_documents_by_project,
    save_uploaded_file,
    update_document_extraction_metadata,
    update_document_status,
)
from backend.app.services.project_service import create_project


def _session_factory(workspace_tmp_path: Path):
    database_path = workspace_tmp_path / "document_service.db"
    settings = Settings(
        app_name="Test App",
        app_version="0.1.0",
        environment="test",
        data_dir=workspace_tmp_path,
        upload_dir=workspace_tmp_path / "uploads",
        export_dir=workspace_tmp_path / "exports",
        database_url=f"sqlite:///{database_path.as_posix()}",
        provider_mode="local",
    )
    database_engine = create_database_engine(settings)
    init_database(database_engine)
    return get_session_factory(database_engine), database_engine, settings


def test_save_uploaded_file_writes_to_project_document_directory(workspace_tmp_path: Path) -> None:
    upload_dir = workspace_tmp_path / "uploads"

    saved_file = save_uploaded_file(
        upload_dir=upload_dir,
        project_id=5,
        original_filename="../Research Draft!.PDF",
        file_content=b"local document bytes",
    )

    assert saved_file.original_filename == "../Research Draft!.PDF"
    assert saved_file.stored_filename.endswith("_Research_Draft.pdf")
    assert saved_file.file_path.exists()
    assert saved_file.file_path.read_bytes() == b"local document bytes"
    assert saved_file.file_size_bytes == len(b"local document bytes")
    assert saved_file.file_path.parent == (upload_dir / "projects" / "5" / "documents").resolve(
        strict=False
    )


def test_create_document_record_persists_saved_file_metadata(workspace_tmp_path: Path) -> None:
    session_factory, database_engine, settings = _session_factory(workspace_tmp_path)

    with session_factory() as session:
        project = create_project(session, ProjectCreate(name="Document project"))
        saved_file = save_uploaded_file(
            settings.upload_dir,
            project.id,
            "paper.pdf",
            b"pdf placeholder",
        )
        document = create_document_record(
            session,
            DocumentCreate(
                project_id=project.id,
                original_filename=saved_file.original_filename,
                mime_type="application/pdf",
                file_size_bytes=saved_file.file_size_bytes,
            ),
            stored_filename=saved_file.stored_filename,
            file_path=saved_file.file_path,
        )

        assert document.id is not None
        assert document.project_id == project.id
        assert document.original_filename == "paper.pdf"
        assert document.stored_filename == saved_file.stored_filename
        assert document.file_path == str(saved_file.file_path)
        assert document.mime_type == "application/pdf"
        assert document.file_size_bytes == len(b"pdf placeholder")
        assert document.status == "stored"

    database_engine.dispose()


def test_update_document_status_strips_and_persists_status(workspace_tmp_path: Path) -> None:
    session_factory, database_engine, settings = _session_factory(workspace_tmp_path)

    with session_factory() as session:
        project = create_project(session, ProjectCreate(name="Status project"))
        saved_file = save_uploaded_file(settings.upload_dir, project.id, "paper.pdf", b"content")
        document = create_document_record(
            session,
            DocumentCreate(project_id=project.id, original_filename="paper.pdf"),
            saved_file.stored_filename,
            saved_file.file_path,
        )

        updated = update_document_status(session, document, " processing ")

        assert updated.status == "processing"

    database_engine.dispose()


def test_count_words_returns_simple_local_word_count() -> None:
    assert count_words("Local extraction works.") == 3
    assert count_words("  ") == 0


def test_is_ocr_likely_needed_uses_low_text_threshold() -> None:
    assert is_ocr_likely_needed(0) is True
    assert is_ocr_likely_needed(MIN_EXTRACTED_WORDS_FOR_TEXT - 1) is True
    assert is_ocr_likely_needed(MIN_EXTRACTED_WORDS_FOR_TEXT) is False


def test_update_document_extraction_metadata_persists_counts_and_error(
    workspace_tmp_path: Path,
) -> None:
    session_factory, database_engine, settings = _session_factory(workspace_tmp_path)

    with session_factory() as session:
        project = create_project(session, ProjectCreate(name="Extraction project"))
        saved_file = save_uploaded_file(settings.upload_dir, project.id, "paper.pdf", b"content")
        document = create_document_record(
            session,
            DocumentCreate(project_id=project.id, original_filename="paper.pdf"),
            saved_file.stored_filename,
            saved_file.file_path,
        )

        updated = update_document_extraction_metadata(
            session,
            document,
            page_count=2,
            word_count=120,
            status=" extracted ",
            extraction_error=" ",
        )

        assert updated.page_count == 2
        assert updated.word_count == 120
        assert updated.status == "extracted"
        assert updated.extraction_error is None

        failed = update_document_extraction_metadata(
            session,
            updated,
            page_count=None,
            word_count=None,
            status="extraction_failed",
            extraction_error="Could not extract text",
        )

        assert failed.page_count is None
        assert failed.word_count is None
        assert failed.status == "extraction_failed"
        assert failed.extraction_error == "Could not extract text"

    database_engine.dispose()


def test_update_document_status_rejects_empty_status(workspace_tmp_path: Path) -> None:
    session_factory, database_engine, settings = _session_factory(workspace_tmp_path)

    with session_factory() as session:
        project = create_project(session, ProjectCreate(name="Invalid status project"))
        saved_file = save_uploaded_file(settings.upload_dir, project.id, "paper.pdf", b"content")
        document = create_document_record(
            session,
            DocumentCreate(project_id=project.id, original_filename="paper.pdf"),
            saved_file.stored_filename,
            saved_file.file_path,
        )

        with pytest.raises(ValueError, match="Document status cannot be empty"):
            update_document_status(session, document, "   ")

    database_engine.dispose()


def test_list_documents_by_project_returns_only_project_documents(workspace_tmp_path: Path) -> None:
    session_factory, database_engine, settings = _session_factory(workspace_tmp_path)

    with session_factory() as session:
        first_project = create_project(session, ProjectCreate(name="First"))
        second_project = create_project(session, ProjectCreate(name="Second"))

        first_saved_file = save_uploaded_file(
            settings.upload_dir, first_project.id, "first.pdf", b"first"
        )
        second_saved_file = save_uploaded_file(
            settings.upload_dir, second_project.id, "second.pdf", b"second"
        )
        create_document_record(
            session,
            DocumentCreate(project_id=first_project.id, original_filename="first.pdf"),
            first_saved_file.stored_filename,
            first_saved_file.file_path,
        )
        second_document = create_document_record(
            session,
            DocumentCreate(project_id=second_project.id, original_filename="second.pdf"),
            second_saved_file.stored_filename,
            second_saved_file.file_path,
        )

        documents = list_documents_by_project(session, second_project.id)

        assert documents == [second_document]

    database_engine.dispose()
