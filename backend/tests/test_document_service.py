import json
from pathlib import Path

import pytest

from backend.app.core.config import Settings
from backend.app.core.database import create_database_engine, get_session_factory, init_database
from backend.app.schemas.document import DocumentCreate
from backend.app.schemas.project import ProjectCreate
from backend.app.services.document_service import (
    MIN_EXTRACTED_WORDS_FOR_TEXT,
    DocumentProcessingError,
    count_words,
    create_document_overview_local_analysis,
    create_document_record,
    create_document_research_info_local_analysis,
    create_document_section_summaries_local_analysis,
    create_section_detection_analysis,
    get_document_section_summaries,
    is_ocr_likely_needed,
    list_documents_by_project,
    save_text_processing_artifacts,
    save_uploaded_file,
    update_document_extraction_metadata,
    update_document_status,
)
from backend.app.services.project_service import create_project
from backend.app.services.section_detection import detect_sections
from backend.app.services.text_cleaning import run_text_cleaning_pipeline


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


def test_save_text_processing_artifacts_writes_extracted_and_cleaned_text(
    workspace_tmp_path: Path,
) -> None:
    pdf_path = workspace_tmp_path / "paper.pdf"
    pdf_path.write_bytes(b"original pdf bytes")
    cleaning_result = run_text_cleaning_pipeline(
        "Header\n1\nThis docu-\nment has noisy   text.\nHeader\n2\nHeader\n3"
    )

    artifacts = save_text_processing_artifacts(pdf_path, cleaning_result)

    assert pdf_path.read_bytes() == b"original pdf bytes"
    assert artifacts.extracted_text_path == workspace_tmp_path / "paper.extracted.txt"
    assert artifacts.cleaned_text_path == workspace_tmp_path / "paper.cleaned.txt"
    assert (
        artifacts.extracted_text_path.read_text(encoding="utf-8") == cleaning_result.original_text
    )
    assert artifacts.cleaned_text_path.read_text(encoding="utf-8") == cleaning_result.cleaned_text


def test_create_section_detection_analysis_persists_structured_sections(
    workspace_tmp_path: Path,
) -> None:
    session_factory, database_engine, settings = _session_factory(workspace_tmp_path)

    with session_factory() as session:
        project = create_project(session, ProjectCreate(name="Section project"))
        saved_file = save_uploaded_file(settings.upload_dir, project.id, "paper.pdf", b"content")
        document = create_document_record(
            session,
            DocumentCreate(project_id=project.id, original_filename="paper.pdf"),
            saved_file.stored_filename,
            saved_file.file_path,
        )
        sections = detect_sections(
            "Research Title\n\nAbstract\nShort abstract.\n\nIntroduction\nOpening text."
        )

        analysis = create_section_detection_analysis(session, document, sections)
        payload = json.loads(analysis.content)

        assert analysis.project_id == project.id
        assert analysis.document_id == document.id
        assert analysis.analysis_type == "section_detection"
        assert analysis.provider_mode == "local"
        assert payload[0]["section_name"] == "Title"
        assert payload[1]["detected_heading"] == "Abstract"
        assert payload[1]["confidence"] == 0.95

    database_engine.dispose()


def test_create_document_overview_local_analysis_persists_output_json(
    workspace_tmp_path: Path,
) -> None:
    session_factory, database_engine, settings = _session_factory(workspace_tmp_path)

    with session_factory() as session:
        project = create_project(session, ProjectCreate(name="Local overview project"))
        saved_file = save_uploaded_file(settings.upload_dir, project.id, "paper.pdf", b"content")
        document = create_document_record(
            session,
            DocumentCreate(project_id=project.id, original_filename="paper.pdf"),
            saved_file.stored_filename,
            saved_file.file_path,
        )
        output_json = {
            "keywords": [{"keyword": "retrieval", "score": 0.75, "frequency": 3}],
            "statistics": {
                "total_word_count": 120,
                "reference_count_estimate": 4,
            },
        }

        analysis = create_document_overview_local_analysis(session, document, output_json)
        payload = json.loads(analysis.content)

        assert analysis.project_id == project.id
        assert analysis.document_id == document.id
        assert analysis.analysis_type == "document_overview_local"
        assert analysis.title == "Local document overview analysis"
        assert analysis.provider_mode == "local"
        assert payload == output_json

    database_engine.dispose()


def test_create_document_overview_local_analysis_rejects_non_serializable_output(
    workspace_tmp_path: Path,
) -> None:
    session_factory, database_engine, settings = _session_factory(workspace_tmp_path)

    with session_factory() as session:
        project = create_project(session, ProjectCreate(name="Invalid overview project"))
        saved_file = save_uploaded_file(settings.upload_dir, project.id, "paper.pdf", b"content")
        document = create_document_record(
            session,
            DocumentCreate(project_id=project.id, original_filename="paper.pdf"),
            saved_file.stored_filename,
            saved_file.file_path,
        )

        with pytest.raises(ValueError, match="JSON serializable"):
            create_document_overview_local_analysis(
                session,
                document,
                {"invalid": {"not", "json"}},
            )

    database_engine.dispose()


def test_create_document_section_summaries_local_analysis_persists_output_json(
    workspace_tmp_path: Path,
) -> None:
    session_factory, database_engine, settings = _session_factory(workspace_tmp_path)

    with session_factory() as session:
        project = create_project(session, ProjectCreate(name="Section summary project"))
        saved_file = save_uploaded_file(settings.upload_dir, project.id, "paper.pdf", b"content")
        document = create_document_record(
            session,
            DocumentCreate(project_id=project.id, original_filename="paper.pdf"),
            saved_file.stored_filename,
            saved_file.file_path,
        )
        sections = detect_sections(
            "Introduction\n"
            "Retrieval supports local analysis. "
            "Students use evidence in thesis writing. "
            "Local summaries preserve source wording.\n\n"
            "References\n"
            "[1] Smith, J. Local retrieval."
        )
        create_section_detection_analysis(session, document, sections)

        analysis = create_document_section_summaries_local_analysis(session, document.id)

        assert analysis is not None
        payload = json.loads(analysis.content)
        assert analysis.project_id == project.id
        assert analysis.document_id == document.id
        assert analysis.analysis_type == "section_summaries_local"
        assert analysis.title == "Local section summaries"
        assert analysis.provider_mode == "local"
        assert payload["document_id"] == document.id
        assert payload["source_section_names"] == ["Introduction"]
        assert payload["summaries"][0]["section_type"] == "introduction"
        assert "Retrieval supports local analysis." in payload["summaries"][0]["summary"]

    database_engine.dispose()


def test_get_document_section_summaries_keeps_best_substantive_section(
    workspace_tmp_path: Path,
) -> None:
    session_factory, database_engine, settings = _session_factory(workspace_tmp_path)

    with session_factory() as session:
        project = create_project(session, ProjectCreate(name="Best summary project"))
        saved_file = save_uploaded_file(settings.upload_dir, project.id, "paper.pdf", b"content")
        document = create_document_record(
            session,
            DocumentCreate(project_id=project.id, original_filename="paper.pdf"),
            saved_file.stored_filename,
            saved_file.file_path,
        )
        sections = detect_sections(
            "Introduction\n"
            "1.1 Background 1.2 Objectives 1.3 Research Questions\n\n"
            "Introduction\n"
            "Retrieval supports local analysis for thesis writers. "
            "Students use evidence to review literature faster.\n\n"
            "Literature Review\n"
            "Prior studies show that source-grounded retrieval improves academic review."
        )
        create_section_detection_analysis(session, document, sections)

        section_summaries = get_document_section_summaries(session, document.id)

        assert section_summaries is not None
        summaries_by_type = {
            summary.section_type: summary.summary for summary in section_summaries.summaries
        }
        assert set(summaries_by_type) == {"introduction", "literature_review"}
        assert "1.1 Background" not in summaries_by_type["introduction"]
        assert "Retrieval supports local analysis" in summaries_by_type["introduction"]
        assert "Prior studies show" in summaries_by_type["literature_review"]

    database_engine.dispose()


def test_create_document_section_summaries_local_analysis_returns_none_for_missing_document(
    workspace_tmp_path: Path,
) -> None:
    session_factory, database_engine, _settings = _session_factory(workspace_tmp_path)

    with session_factory() as session:
        assert create_document_section_summaries_local_analysis(session, 999) is None

    database_engine.dispose()


def test_create_document_research_info_local_analysis_persists_output_json(
    workspace_tmp_path: Path,
) -> None:
    session_factory, database_engine, settings = _session_factory(workspace_tmp_path)

    with session_factory() as session:
        project = create_project(session, ProjectCreate(name="Research info project"))
        saved_file = save_uploaded_file(settings.upload_dir, project.id, "paper.pdf", b"content")
        cleaned_text_path = workspace_tmp_path / "paper.cleaned.txt"
        cleaned_text_path.write_text(
            "Introduction\n"
            "The problem is that thesis writers lack source-grounded review tools. "
            "The objective is to evaluate local document analysis. "
            "RQ1: How does local retrieval affect thesis review?\n\n"
            "Methodology\n"
            "The methodology used a survey with 48 graduate students. "
            "Variables included review time and citation accuracy.\n\n"
            "Results\n"
            "The findings revealed improved citation accuracy.\n\n"
            "Conclusion\n"
            "The limitation is that the sample used one university. "
            "Future work should explore larger datasets.",
            encoding="utf-8",
        )
        document = create_document_record(
            session,
            DocumentCreate(project_id=project.id, original_filename="paper.pdf"),
            saved_file.stored_filename,
            saved_file.file_path,
        )
        document.cleaned_text_path = str(cleaned_text_path)
        session.add(document)
        session.flush()
        create_section_detection_analysis(
            session,
            document,
            detect_sections(cleaned_text_path.read_text(encoding="utf-8")),
        )

        analysis = create_document_research_info_local_analysis(session, document.id)

        assert analysis is not None
        payload = json.loads(analysis.content)
        assert analysis.project_id == project.id
        assert analysis.document_id == document.id
        assert analysis.analysis_type == "research_info_local"
        assert analysis.title == "Local research information extraction"
        assert analysis.provider_mode == "local"
        assert payload["document_id"] == document.id
        assert payload["filename"] == "paper.pdf"
        assert "lack source-grounded review tools" in (
            payload["fields"]["research_problem"]["extracted_text"]
        )
        assert payload["fields"]["research_problem"]["source_section"] == "Introduction"
        assert payload["fields"]["research_problem"]["confidence"] > 0
        assert "larger datasets" in payload["fields"]["future_work"]["extracted_text"]

    database_engine.dispose()


def test_create_document_research_info_local_analysis_requires_cleaned_text(
    workspace_tmp_path: Path,
) -> None:
    session_factory, database_engine, settings = _session_factory(workspace_tmp_path)

    with session_factory() as session:
        project = create_project(session, ProjectCreate(name="Missing text project"))
        saved_file = save_uploaded_file(settings.upload_dir, project.id, "paper.pdf", b"content")
        document = create_document_record(
            session,
            DocumentCreate(project_id=project.id, original_filename="paper.pdf"),
            saved_file.stored_filename,
            saved_file.file_path,
        )

        with pytest.raises(DocumentProcessingError, match="Cleaned text is not available"):
            create_document_research_info_local_analysis(session, document.id)

    database_engine.dispose()


def test_create_document_research_info_local_analysis_returns_none_for_missing_document(
    workspace_tmp_path: Path,
) -> None:
    session_factory, database_engine, _settings = _session_factory(workspace_tmp_path)

    with session_factory() as session:
        assert create_document_research_info_local_analysis(session, 999) is None

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
            extracted_text_path=workspace_tmp_path / "paper.extracted.txt",
            cleaned_text_path=workspace_tmp_path / "paper.cleaned.txt",
            cleaning_warnings=["warning one", "warning two"],
        )

        assert updated.page_count == 2
        assert updated.word_count == 120
        assert updated.status == "extracted"
        assert updated.extraction_error is None
        assert updated.extracted_text_path == str(workspace_tmp_path / "paper.extracted.txt")
        assert updated.cleaned_text_path == str(workspace_tmp_path / "paper.cleaned.txt")
        assert updated.cleaning_warnings == "warning one\nwarning two"

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
