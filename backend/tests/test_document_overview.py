import json
from pathlib import Path

import pytest

from backend.app.core.config import Settings
from backend.app.core.database import create_database_engine, get_session_factory, init_database
from backend.app.models.analysis import Analysis
from backend.app.schemas.document import DocumentCreate
from backend.app.schemas.project import ProjectCreate
from backend.app.services.chunking import TextChunk, replace_document_chunks
from backend.app.services.document_overview import get_document_overview
from backend.app.services.document_service import (
    create_document_record,
    create_section_detection_analysis,
    save_uploaded_file,
    update_document_extraction_metadata,
)
from backend.app.services.project_service import create_project
from backend.app.services.section_detection import detect_sections


def _session_factory(workspace_tmp_path: Path):
    database_path = workspace_tmp_path / "document_overview.db"
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


def _create_document(session, settings, status: str = "stored"):
    project = create_project(session, ProjectCreate(name="Overview project"))
    saved_file = save_uploaded_file(settings.upload_dir, project.id, "paper.pdf", b"content")
    return create_document_record(
        session,
        DocumentCreate(project_id=project.id, original_filename="paper.pdf"),
        saved_file.stored_filename,
        saved_file.file_path,
        status=status,
    )


def test_get_document_overview_returns_processed_document_summary(
    workspace_tmp_path: Path,
) -> None:
    session_factory, database_engine, settings = _session_factory(workspace_tmp_path)

    with session_factory() as session:
        document = _create_document(session, settings)
        updated_document = update_document_extraction_metadata(
            session,
            document,
            page_count=4,
            word_count=1_250,
            status="processed",
            cleaning_warnings=["Removed repeated page header"],
        )
        sections = detect_sections(
            "Research Title\n\nAbstract\nShort abstract.\n\nIntroduction\nOpening text."
        )
        create_section_detection_analysis(session, updated_document, sections)
        replace_document_chunks(
            session,
            updated_document.id,
            [
                TextChunk(
                    chunk_index=0,
                    section_name="Abstract",
                    page_start=1,
                    page_end=1,
                    text="abstract chunk",
                    word_count=2,
                ),
                TextChunk(
                    chunk_index=1,
                    section_name="Introduction",
                    page_start=2,
                    page_end=3,
                    text="introduction chunk",
                    word_count=2,
                ),
            ],
        )

        overview = get_document_overview(session, updated_document.id)

        assert overview is not None
        assert overview.filename == "paper.pdf"
        assert overview.status == "processed"
        assert overview.page_count == 4
        assert overview.word_count == 1_250
        assert overview.chunk_count == 2
        assert [section.section_name for section in overview.detected_sections] == [
            "Title",
            "Abstract",
            "Introduction",
        ]
        assert overview.extraction_warnings == ["Removed repeated page header"]
        assert overview.processing_summary.message == (
            "Document processed locally with 3 detected sections and 2 stored chunks."
        )
        assert overview.processing_summary.status == "processed"
        assert overview.processing_summary.is_complete is True
        assert overview.processing_summary.requires_attention is False
        assert overview.to_dict()["detected_sections"][1]["section_name"] == "Abstract"
        assert overview.to_dict()["processing_summary"]["is_complete"] is True

    database_engine.dispose()


def test_get_document_overview_combines_extraction_and_cleaning_warnings(
    workspace_tmp_path: Path,
) -> None:
    session_factory, database_engine, settings = _session_factory(workspace_tmp_path)

    with session_factory() as session:
        document = _create_document(session, settings)
        updated_document = update_document_extraction_metadata(
            session,
            document,
            page_count=1,
            word_count=1,
            status="ocr_needed",
            extraction_error="Very little extractable text was found.",
            cleaning_warnings=["Cleaned text is very short", "Possible scanned PDF"],
        )

        overview = get_document_overview(session, updated_document.id)

        assert overview is not None
        assert overview.extraction_warnings == [
            "Very little extractable text was found.",
            "Cleaned text is very short",
            "Possible scanned PDF",
        ]
        assert "OCR may be needed" in overview.processing_summary.message
        assert overview.processing_summary.requires_attention is True

    database_engine.dispose()


def test_get_document_overview_returns_none_for_missing_document(
    workspace_tmp_path: Path,
) -> None:
    session_factory, database_engine, _ = _session_factory(workspace_tmp_path)

    with session_factory() as session:
        assert get_document_overview(session, 999) is None

    database_engine.dispose()


def test_get_document_overview_rejects_invalid_document_id(workspace_tmp_path: Path) -> None:
    session_factory, database_engine, _ = _session_factory(workspace_tmp_path)

    with session_factory() as session:
        with pytest.raises(ValueError, match="positive integer"):
            get_document_overview(session, 0)

    database_engine.dispose()


def test_get_document_overview_handles_malformed_section_analysis(
    workspace_tmp_path: Path,
) -> None:
    session_factory, database_engine, settings = _session_factory(workspace_tmp_path)

    with session_factory() as session:
        document = _create_document(session, settings, status="processed")
        session.add(
            Analysis(
                project_id=document.project_id,
                document_id=document.id,
                analysis_type="section_detection",
                title="Malformed sections",
                content="{not-json",
                provider_mode="local",
            )
        )
        session.commit()

        overview = get_document_overview(session, document.id)

        assert overview is not None
        assert overview.detected_sections == []
        assert "0 detected sections" in overview.processing_summary.message

    database_engine.dispose()


def test_get_document_overview_uses_latest_section_analysis(
    workspace_tmp_path: Path,
) -> None:
    session_factory, database_engine, settings = _session_factory(workspace_tmp_path)

    with session_factory() as session:
        document = _create_document(session, settings, status="processed")
        session.add(
            Analysis(
                project_id=document.project_id,
                document_id=document.id,
                analysis_type="section_detection",
                title="Old sections",
                content=json.dumps([{"section_name": "Old", "detected_heading": "Old"}]),
                provider_mode="local",
            )
        )
        session.flush()
        session.add(
            Analysis(
                project_id=document.project_id,
                document_id=document.id,
                analysis_type="section_detection",
                title="New sections",
                content=json.dumps([{"section_name": "New", "detected_heading": "New"}]),
                provider_mode="local",
            )
        )
        session.commit()

        overview = get_document_overview(session, document.id)

        assert overview is not None
        assert [section.section_name for section in overview.detected_sections] == ["New"]

    database_engine.dispose()


def test_get_document_overview_clamps_malformed_section_confidence(
    workspace_tmp_path: Path,
) -> None:
    session_factory, database_engine, settings = _session_factory(workspace_tmp_path)

    with session_factory() as session:
        document = _create_document(session, settings, status="processed")
        session.add(
            Analysis(
                project_id=document.project_id,
                document_id=document.id,
                analysis_type="section_detection",
                title="Sections with bad confidence",
                content=json.dumps(
                    [
                        {
                            "section_name": "Abstract",
                            "detected_heading": "Abstract",
                            "confidence": 2.5,
                        },
                        {
                            "section_name": "Introduction",
                            "detected_heading": "Introduction",
                            "confidence": -1,
                        },
                    ]
                ),
                provider_mode="local",
            )
        )
        session.commit()

        overview = get_document_overview(session, document.id)

        assert overview is not None
        assert [section.confidence for section in overview.detected_sections] == [1.0, 0.0]

    database_engine.dispose()
