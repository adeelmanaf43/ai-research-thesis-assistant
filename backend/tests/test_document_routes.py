import json
from collections.abc import Generator
from pathlib import Path

import fitz
import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.config import Settings, get_settings
from backend.app.core.database import (
    create_database_engine,
    get_db,
    get_session_factory,
    init_database,
)
from backend.app.main import create_app
from backend.app.models.analysis import Analysis
from backend.app.models.chat_history import ChatHistory
from backend.app.models.chunk import Chunk
from backend.app.models.document import Document
from backend.app.schemas.document import DocumentCreate
from backend.app.schemas.project import ProjectCreate
from backend.app.services.chunking import ChunkPersistenceError
from backend.app.services.document_extraction import ExtractedPDF
from backend.app.services.document_service import (
    OCR_NEEDED_MESSAGE,
    DocumentProcessingError,
    DocumentStorageError,
    create_document_record,
)
from backend.app.services.project_service import create_project


@pytest.fixture
def document_api_settings(workspace_tmp_path: Path) -> Settings:
    return Settings(
        app_name="Test App",
        app_version="0.1.0",
        environment="test",
        data_dir=workspace_tmp_path,
        upload_dir=workspace_tmp_path / "uploads",
        export_dir=workspace_tmp_path / "exports",
        database_url=f"sqlite:///{(workspace_tmp_path / 'document_routes.db').as_posix()}",
        provider_mode="local",
        max_upload_file_size_bytes=50_000,
    )


@pytest.fixture
def document_api_client(document_api_settings: Settings):
    database_engine = create_database_engine(document_api_settings)
    init_database(database_engine)
    session_factory = get_session_factory(database_engine)
    test_app = create_app()

    def override_get_db() -> Generator[Session, None, None]:
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    test_app.dependency_overrides[get_db] = override_get_db
    test_app.dependency_overrides[get_settings] = lambda: document_api_settings
    transport = httpx.ASGITransport(app=test_app)

    try:
        yield httpx.AsyncClient(transport=transport, base_url="http://testserver")
    finally:
        test_app.dependency_overrides.clear()
        database_engine.dispose()


def _create_project(settings: Settings) -> int:
    database_engine = create_database_engine(settings)
    session_factory = get_session_factory(database_engine)
    with session_factory() as session:
        project = create_project(session, ProjectCreate(name="Upload project"))
        project_id = project.id
    database_engine.dispose()
    return project_id


def _create_document_metadata(
    settings: Settings,
    *,
    project_id: int | None = None,
    filename: str = "paper.pdf",
    status: str = "processed",
    page_count: int | None = 1,
    word_count: int | None = 20,
) -> int:
    database_engine = create_database_engine(settings)
    session_factory = get_session_factory(database_engine)
    with session_factory() as session:
        if project_id is None:
            project = create_project(session, ProjectCreate(name="Document project"))
            project_id = project.id

        document = create_document_record(
            session,
            DocumentCreate(
                project_id=project_id,
                original_filename=filename,
                mime_type="application/pdf",
                file_size_bytes=128,
            ),
            stored_filename=f"stored-{filename}",
            file_path=settings.upload_dir / filename,
            status=status,
        )
        document.page_count = page_count
        document.word_count = word_count
        session.add(document)
        session.commit()
        session.refresh(document)
        document_id = document.id

    database_engine.dispose()
    return document_id


def _create_analysis_ready_document(settings: Settings) -> int:
    database_engine = create_database_engine(settings)
    session_factory = get_session_factory(database_engine)
    with session_factory() as session:
        project = create_project(session, ProjectCreate(name="Analysis project"))
        cleaned_text_path = settings.upload_dir / "analysis-ready.cleaned.txt"
        cleaned_text_path.parent.mkdir(parents=True, exist_ok=True)
        cleaned_text_path.write_text(
            "Introduction\n"
            "Retrieval retrieval supports local analysis.\n\n"
            "References\n"
            "[1] Smith, J. Local retrieval.",
            encoding="utf-8",
        )
        document = create_document_record(
            session,
            DocumentCreate(
                project_id=project.id,
                original_filename="analysis-ready.pdf",
                mime_type="application/pdf",
                file_size_bytes=256,
            ),
            stored_filename="analysis-ready.pdf",
            file_path=settings.upload_dir / "analysis-ready.pdf",
            status="processed",
        )
        document.cleaned_text_path = str(cleaned_text_path)
        session.add(document)
        session.flush()
        session.add_all(
            [
                Analysis(
                    project_id=project.id,
                    document_id=document.id,
                    analysis_type="section_detection",
                    title="Detected sections",
                    content=json.dumps(
                        [
                            {
                                "section_type": "introduction",
                                "section_name": "Introduction",
                                "text": (
                                    "The baseline was simple. "
                                    "Retrieval retrieval supports local analysis. "
                                    "Students reported better thesis review "
                                    "with retrieval evidence."
                                ),
                                "confidence": 0.95,
                            },
                            {
                                "section_type": "results",
                                "section_name": "Results",
                                "text": (
                                    "The first result was noisy. "
                                    "Retrieval accuracy improved when clean chunks "
                                    "preserved evidence. "
                                    "Users completed review tasks faster with source evidence."
                                ),
                                "confidence": 0.9,
                            },
                            {
                                "section_type": "references",
                                "section_name": "References",
                                "text": "[1] Smith, J. Local retrieval.",
                                "confidence": 0.95,
                            },
                        ]
                    ),
                    provider_mode="local",
                ),
                Chunk(
                    document_id=document.id,
                    chunk_index=0,
                    section_name="Introduction",
                    text="Retrieval retrieval supports local analysis.",
                    word_count=5,
                    page_start=1,
                    page_end=1,
                ),
                Chunk(
                    document_id=document.id,
                    chunk_index=1,
                    section_name="References",
                    text="[1] Smith, J. Local retrieval.",
                    word_count=4,
                    page_start=1,
                    page_end=1,
                ),
            ]
        )
        session.commit()
        document_id = document.id

    database_engine.dispose()
    return document_id


def _create_research_info_ready_document(settings: Settings) -> int:
    database_engine = create_database_engine(settings)
    session_factory = get_session_factory(database_engine)
    with session_factory() as session:
        project = create_project(session, ProjectCreate(name="Research info project"))
        cleaned_text_path = settings.upload_dir / "research-info-ready.cleaned.txt"
        cleaned_text_path.parent.mkdir(parents=True, exist_ok=True)
        cleaned_text = (
            "Introduction\n"
            "The problem is that thesis writers lack source-grounded review tools. "
            "The objective is to evaluate a local document assistant. "
            "RQ1: How does local retrieval affect thesis review?\n\n"
            "Methodology\n"
            "The methodology used a mixed-method survey and interview approach. "
            "The sample included 48 graduate students and 12 academic freelancers. "
            "Variables included review time, citation accuracy, and confidence.\n\n"
            "Results\n"
            "The findings revealed that retrieval improved citation accuracy.\n\n"
            "Discussion\n"
            "The limitation is that the sample came from one university. "
            "Future work should explore larger datasets and more disciplines."
        )
        cleaned_text_path.write_text(cleaned_text, encoding="utf-8")
        document = create_document_record(
            session,
            DocumentCreate(
                project_id=project.id,
                original_filename="research-info-ready.pdf",
                mime_type="application/pdf",
                file_size_bytes=256,
            ),
            stored_filename="research-info-ready.pdf",
            file_path=settings.upload_dir / "research-info-ready.pdf",
            status="processed",
        )
        document.cleaned_text_path = str(cleaned_text_path)
        session.add(document)
        session.flush()
        session.add(
            Analysis(
                project_id=project.id,
                document_id=document.id,
                analysis_type="section_detection",
                title="Detected sections",
                content=json.dumps(
                    [
                        {
                            "section_type": "introduction",
                            "section_name": "Introduction",
                            "text": (
                                "The problem is that thesis writers lack "
                                "source-grounded review tools. "
                                "The objective is to evaluate a local document assistant. "
                                "RQ1: How does local retrieval affect thesis review?"
                            ),
                            "confidence": 0.95,
                        },
                        {
                            "section_type": "methodology",
                            "section_name": "Methodology",
                            "text": (
                                "The methodology used a mixed-method survey and "
                                "interview approach. The sample included 48 graduate "
                                "students and 12 academic freelancers. Variables "
                                "included review time, citation accuracy, and confidence."
                            ),
                            "confidence": 0.95,
                        },
                        {
                            "section_type": "results",
                            "section_name": "Results",
                            "text": (
                                "The findings revealed that retrieval improved "
                                "citation accuracy."
                            ),
                            "confidence": 0.9,
                        },
                        {
                            "section_type": "discussion",
                            "section_name": "Discussion",
                            "text": (
                                "The limitation is that the sample came from one "
                                "university. Future work should explore larger "
                                "datasets and more disciplines."
                            ),
                            "confidence": 0.9,
                        },
                    ]
                ),
                provider_mode="local",
            )
        )
        session.commit()
        document_id = document.id

    database_engine.dispose()
    return document_id


def _pdf_bytes(page_text: str) -> bytes:
    document = fitz.open()
    page = document.new_page()
    if page_text:
        page.insert_text((72, 72), page_text)
    pdf_content = document.tobytes()
    document.close()
    return pdf_content


@pytest.mark.anyio
async def test_upload_document_route_accepts_pdf_and_creates_record(
    document_api_client: httpx.AsyncClient,
    document_api_settings: Settings,
) -> None:
    project_id = _create_project(document_api_settings)

    async with document_api_client as client:
        response = await client.post(
            f"/api/projects/{project_id}/documents",
            files={"file": ("paper.pdf", b"%PDF-1.4", "application/pdf")},
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["project_id"] == project_id
    assert payload["original_filename"] == "paper.pdf"
    assert payload["mime_type"] == "application/pdf"
    assert payload["file_size_bytes"] == len(b"%PDF-1.4")
    assert payload["page_count"] is None
    assert payload["word_count"] is None
    assert payload["status"] == "extraction_failed"
    assert "Could not extract text from PDF" in payload["extraction_error"]
    assert "file_path" not in payload
    assert "stored_filename" not in payload
    assert len(list(document_api_settings.upload_dir.rglob("*.pdf"))) == 1


@pytest.mark.anyio
async def test_list_project_documents_route_returns_project_documents(
    document_api_client: httpx.AsyncClient,
    document_api_settings: Settings,
) -> None:
    project_id = _create_project(document_api_settings)
    _create_document_metadata(
        document_api_settings,
        project_id=project_id,
        filename="first.pdf",
    )
    _create_document_metadata(
        document_api_settings,
        project_id=project_id,
        filename="second.pdf",
        status="ocr_needed",
        page_count=2,
        word_count=3,
    )

    async with document_api_client as client:
        response = await client.get(f"/api/projects/{project_id}/documents")

    assert response.status_code == 200
    payload = response.json()
    assert [document["original_filename"] for document in payload] == [
        "second.pdf",
        "first.pdf",
    ]
    assert payload[0]["status"] == "ocr_needed"
    assert payload[0]["page_count"] == 2
    assert payload[0]["word_count"] == 3
    assert "file_path" not in payload[0]
    assert "stored_filename" not in payload[0]


@pytest.mark.anyio
async def test_list_project_documents_route_returns_404_for_missing_project(
    document_api_client: httpx.AsyncClient,
) -> None:
    async with document_api_client as client:
        response = await client.get("/api/projects/999/documents")

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Project not found. Create the project before listing documents."
    )


@pytest.mark.anyio
async def test_get_document_overview_route_returns_processed_document_summary(
    document_api_client: httpx.AsyncClient,
    document_api_settings: Settings,
) -> None:
    document_id = _create_document_metadata(document_api_settings)

    database_engine = create_database_engine(document_api_settings)
    session_factory = get_session_factory(database_engine)
    with session_factory() as session:
        document = session.get(Document, document_id)
        assert document is not None
        document.cleaning_warnings = "Removed repeated page header"
        session.add_all(
            [
                Analysis(
                    project_id=document.project_id,
                    document_id=document.id,
                    analysis_type="section_detection",
                    title="Detected sections",
                    content=json.dumps(
                        [
                            {
                                "section_name": "Abstract",
                                "detected_heading": "Abstract",
                                "confidence": 0.95,
                            }
                        ]
                    ),
                    provider_mode="local",
                ),
                Chunk(
                    document_id=document.id,
                    chunk_index=0,
                    section_name="Abstract",
                    text="chunk text",
                    word_count=2,
                    page_start=1,
                    page_end=1,
                ),
            ]
        )
        session.commit()
    database_engine.dispose()

    async with document_api_client as client:
        response = await client.get(f"/api/documents/{document_id}/overview")

    assert response.status_code == 200
    payload = response.json()
    assert payload["document_id"] == document_id
    assert payload["filename"] == "paper.pdf"
    assert payload["status"] == "processed"
    assert payload["page_count"] == 1
    assert payload["word_count"] == 20
    assert payload["chunk_count"] == 1
    assert payload["detected_sections"] == [
        {
            "section_name": "Abstract",
            "detected_heading": "Abstract",
            "confidence": 0.95,
        }
    ]
    assert payload["extraction_warnings"] == ["Removed repeated page header"]
    assert payload["processing_summary"] == {
        "status": "processed",
        "message": "Document processed locally with 1 detected sections and 1 stored chunks.",
        "is_complete": True,
        "requires_attention": False,
        "next_step": "Review the overview or continue with the next local analysis step.",
    }


@pytest.mark.anyio
async def test_get_document_overview_route_returns_ocr_warning_summary(
    document_api_client: httpx.AsyncClient,
    document_api_settings: Settings,
) -> None:
    document_id = _create_document_metadata(
        document_api_settings,
        filename="scanned.pdf",
        status="ocr_needed",
        page_count=1,
        word_count=1,
    )

    database_engine = create_database_engine(document_api_settings)
    session_factory = get_session_factory(database_engine)
    with session_factory() as session:
        document = session.get(Document, document_id)
        assert document is not None
        document.extraction_error = OCR_NEEDED_MESSAGE
        document.cleaning_warnings = "Cleaned text is very short"
        session.add(document)
        session.commit()
    database_engine.dispose()

    async with document_api_client as client:
        response = await client.get(f"/api/documents/{document_id}/overview")

    assert response.status_code == 200
    payload = response.json()
    assert payload["document_id"] == document_id
    assert payload["filename"] == "scanned.pdf"
    assert payload["status"] == "ocr_needed"
    assert payload["page_count"] == 1
    assert payload["word_count"] == 1
    assert payload["chunk_count"] == 0
    assert payload["detected_sections"] == []
    assert payload["extraction_warnings"] == [
        OCR_NEEDED_MESSAGE,
        "Cleaned text is very short",
    ]
    assert payload["processing_summary"] == {
        "status": "ocr_needed",
        "message": "Document was saved, but very little text was extracted. OCR may be needed.",
        "is_complete": False,
        "requires_attention": True,
        "next_step": "Use a text-based PDF or add OCR support in a later workflow.",
    }


@pytest.mark.anyio
async def test_get_document_overview_route_returns_404_for_missing_document(
    document_api_client: httpx.AsyncClient,
) -> None:
    async with document_api_client as client:
        response = await client.get("/api/documents/999/overview")

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Document not found. Upload a document or use an existing document ID."
    )


@pytest.mark.anyio
async def test_get_document_overview_route_returns_user_friendly_invalid_id_error(
    document_api_client: httpx.AsyncClient,
) -> None:
    async with document_api_client as client:
        response = await client.get("/api/documents/0/overview")

    assert response.status_code == 422
    assert response.json()["detail"] == "Document ID must be a positive integer."


@pytest.mark.anyio
async def test_create_document_local_overview_analysis_route_persists_analysis(
    document_api_client: httpx.AsyncClient,
    document_api_settings: Settings,
) -> None:
    document_id = _create_analysis_ready_document(document_api_settings)

    async with document_api_client as client:
        response = await client.post(f"/api/documents/{document_id}/analysis/local-overview")

    assert response.status_code == 201
    payload = response.json()
    assert payload["document_id"] == document_id
    assert payload["analysis_type"] == "document_overview_local"
    assert payload["provider_mode"] == "local"
    assert payload["title"] == "Local document overview analysis"
    assert payload["output_json"]["document_id"] == document_id
    assert payload["output_json"]["filename"] == "analysis-ready.pdf"
    assert payload["output_json"]["keywords"][0]["keyword"] == "retrieval"
    assert payload["output_json"]["statistics"]["word_count_by_section"] == {
        "Introduction": 17,
        "Results": 21,
        "References": 4,
    }
    assert payload["output_json"]["statistics"]["chunk_count_by_section"] == {
        "Introduction": 1,
        "References": 1,
    }
    assert payload["output_json"]["statistics"]["reference_count_estimate"] == 1


@pytest.mark.anyio
async def test_get_document_local_overview_analysis_route_returns_latest_analysis(
    document_api_client: httpx.AsyncClient,
    document_api_settings: Settings,
) -> None:
    document_id = _create_analysis_ready_document(document_api_settings)

    async with document_api_client as client:
        created_response = await client.post(
            f"/api/documents/{document_id}/analysis/local-overview"
        )
        fetched_response = await client.get(f"/api/documents/{document_id}/analysis/local-overview")

    assert created_response.status_code == 201
    assert fetched_response.status_code == 200
    assert fetched_response.json()["id"] == created_response.json()["id"]
    assert fetched_response.json()["output_json"]["statistics"]["total_word_count"] == 11


@pytest.mark.anyio
async def test_get_document_section_summaries_route_returns_supported_section_summaries(
    document_api_client: httpx.AsyncClient,
    document_api_settings: Settings,
) -> None:
    document_id = _create_analysis_ready_document(document_api_settings)

    async with document_api_client as client:
        response = await client.get(f"/api/documents/{document_id}/summaries/sections")

    assert response.status_code == 200
    payload = response.json()
    assert payload["document_id"] == document_id
    assert payload["source_section_names"] == ["Introduction", "Results"]
    assert payload["limitations"] == [
        (
            "Summaries are extractive and local; they select source sentences "
            "instead of generating new prose."
        )
    ]
    assert [summary["section_name"] for summary in payload["summaries"]] == [
        "Introduction",
        "Results",
    ]
    assert payload["summaries"][0]["confidence"] > 0.8
    assert "Retrieval retrieval supports local analysis." in payload["summaries"][0]["summary"]
    assert "source_sentence_indexes" in payload["summaries"][0]
    assert payload["summaries"][0]["limitations"] == [
        (
            "Extractive summary uses original sentences only and does not rewrite "
            "or infer missing context."
        )
    ]


@pytest.mark.anyio
async def test_create_document_section_summaries_analysis_route_persists_local_analysis(
    document_api_client: httpx.AsyncClient,
    document_api_settings: Settings,
) -> None:
    document_id = _create_analysis_ready_document(document_api_settings)

    async with document_api_client as client:
        response = await client.post(f"/api/documents/{document_id}/analysis/section-summaries")

    assert response.status_code == 201
    payload = response.json()
    assert payload["document_id"] == document_id
    assert payload["analysis_type"] == "section_summaries_local"
    assert payload["title"] == "Local section summaries"
    assert payload["provider_mode"] == "local"
    assert payload["output_json"]["source_section_names"] == ["Introduction", "Results"]
    assert payload["output_json"]["summaries"][0]["section_type"] == "introduction"

    database_engine = create_database_engine(document_api_settings)
    session_factory = get_session_factory(database_engine)
    with session_factory() as session:
        stored_analysis = session.scalar(select(Analysis).where(Analysis.id == payload["id"]))
        assert stored_analysis is not None
        assert stored_analysis.analysis_type == "section_summaries_local"
        assert stored_analysis.provider_mode == "local"
        stored_payload = json.loads(stored_analysis.content)
        assert stored_payload == payload["output_json"]
    database_engine.dispose()


@pytest.mark.anyio
async def test_create_document_section_summaries_analysis_route_returns_404_for_missing_document(
    document_api_client: httpx.AsyncClient,
) -> None:
    async with document_api_client as client:
        response = await client.post("/api/documents/999/analysis/section-summaries")

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Document not found. Upload a document or use an existing document ID."
    )


@pytest.mark.anyio
async def test_create_document_section_summaries_analysis_route_returns_invalid_id_error(
    document_api_client: httpx.AsyncClient,
) -> None:
    async with document_api_client as client:
        response = await client.post("/api/documents/0/analysis/section-summaries")

    assert response.status_code == 422
    assert response.json()["detail"] == "Document ID must be a positive integer."


@pytest.mark.anyio
async def test_get_document_section_summaries_route_returns_limitation_without_sections(
    document_api_client: httpx.AsyncClient,
    document_api_settings: Settings,
) -> None:
    document_id = _create_document_metadata(document_api_settings)

    async with document_api_client as client:
        response = await client.get(f"/api/documents/{document_id}/summaries/sections")

    assert response.status_code == 200
    payload = response.json()
    assert payload["summaries"] == []
    assert payload["source_section_names"] == []
    assert payload["limitations"] == [
        "No stored section detection output was found. Upload and process the document first."
    ]


@pytest.mark.anyio
async def test_get_document_section_summaries_route_returns_404_for_missing_document(
    document_api_client: httpx.AsyncClient,
) -> None:
    async with document_api_client as client:
        response = await client.get("/api/documents/999/summaries/sections")

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Document not found. Upload a document or use an existing document ID."
    )


@pytest.mark.anyio
async def test_get_document_section_summaries_route_returns_invalid_id_error(
    document_api_client: httpx.AsyncClient,
) -> None:
    async with document_api_client as client:
        response = await client.get("/api/documents/0/summaries/sections")

    assert response.status_code == 422
    assert response.json()["detail"] == "Document ID must be a positive integer."


@pytest.mark.anyio
async def test_search_document_chunks_route_returns_preview_results(
    document_api_client: httpx.AsyncClient,
    document_api_settings: Settings,
) -> None:
    document_id = _create_analysis_ready_document(document_api_settings)

    async with document_api_client as client:
        response = await client.get(
            f"/api/documents/{document_id}/search",
            params={"q": "local analysis retrieval", "top_k": 1},
        )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["chunk_index"] == 0
    assert payload[0]["section_name"] == "Introduction"
    assert payload[0]["page_start"] == 1
    assert payload[0]["page_end"] == 1
    assert payload[0]["score"] > 0
    assert payload[0]["text_preview"] == "Retrieval retrieval supports local analysis."
    assert payload[0]["full_text"] is None
    assert "document_id" not in payload[0]


@pytest.mark.anyio
async def test_search_document_chunks_route_can_include_full_text(
    document_api_client: httpx.AsyncClient,
    document_api_settings: Settings,
) -> None:
    document_id = _create_analysis_ready_document(document_api_settings)

    async with document_api_client as client:
        response = await client.get(
            f"/api/documents/{document_id}/search",
            params={
                "q": "local analysis retrieval",
                "top_k": 1,
                "include_full_text": "true",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["text_preview"] == "Retrieval retrieval supports local analysis."
    assert payload[0]["full_text"] == "Retrieval retrieval supports local analysis."


@pytest.mark.anyio
async def test_search_document_chunks_route_respects_top_k_limit(
    document_api_client: httpx.AsyncClient,
    document_api_settings: Settings,
) -> None:
    document_id = _create_analysis_ready_document(document_api_settings)

    async with document_api_client as client:
        response = await client.get(
            f"/api/documents/{document_id}/search",
            params={"q": "retrieval", "top_k": 1},
        )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["score"] > 0


@pytest.mark.anyio
async def test_search_document_chunks_route_returns_empty_list_for_no_matches(
    document_api_client: httpx.AsyncClient,
    document_api_settings: Settings,
) -> None:
    document_id = _create_analysis_ready_document(document_api_settings)

    async with document_api_client as client:
        response = await client.get(
            f"/api/documents/{document_id}/search",
            params={"q": "quantum astrophysics"},
        )

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.anyio
async def test_search_document_chunks_route_returns_404_for_missing_document(
    document_api_client: httpx.AsyncClient,
) -> None:
    async with document_api_client as client:
        response = await client.get(
            "/api/documents/999/search",
            params={"q": "retrieval"},
        )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Document not found. Upload a document or use an existing document ID."
    )


@pytest.mark.anyio
async def test_search_document_chunks_route_validates_document_id(
    document_api_client: httpx.AsyncClient,
) -> None:
    async with document_api_client as client:
        response = await client.get(
            "/api/documents/0/search",
            params={"q": "retrieval"},
        )

    assert response.status_code == 422
    assert response.json()["detail"] == "Document ID must be a positive integer."


@pytest.mark.anyio
async def test_search_document_chunks_route_validates_query_and_top_k(
    document_api_client: httpx.AsyncClient,
    document_api_settings: Settings,
) -> None:
    document_id = _create_analysis_ready_document(document_api_settings)

    async with document_api_client as client:
        blank_query_response = await client.get(
            f"/api/documents/{document_id}/search",
            params={"q": "   "},
        )
        invalid_top_k_response = await client.get(
            f"/api/documents/{document_id}/search",
            params={"q": "retrieval", "top_k": 0},
        )

    assert blank_query_response.status_code == 422
    assert blank_query_response.json()["detail"] == "Search query must not be empty."
    assert invalid_top_k_response.status_code == 422
    assert invalid_top_k_response.json()["detail"] == "top_k must be a positive integer."


@pytest.mark.anyio
async def test_chat_with_document_route_returns_local_answer_and_stores_history(
    document_api_client: httpx.AsyncClient,
    document_api_settings: Settings,
) -> None:
    document_id = _create_analysis_ready_document(document_api_settings)

    async with document_api_client as client:
        response = await client.post(
            f"/api/documents/{document_id}/chat",
            json={"question": "What supports local analysis?", "top_k": 2},
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["document_id"] == document_id
    assert payload["question"] == "What supports local analysis?"
    assert payload["answer_found"] is True
    assert payload["provider_mode"] == "local"
    assert "Retrieval retrieval supports local analysis." in payload["answer"]
    assert payload["source_chunks"][0]["section_name"] == "Introduction"
    assert payload["source_chunks"][0]["score"] > 0
    assert payload["limitations"]

    database_engine = create_database_engine(document_api_settings)
    session_factory = get_session_factory(database_engine)
    with session_factory() as session:
        stored_chat = session.scalar(
            select(ChatHistory).where(ChatHistory.id == payload["chat_id"])
        )
        assert stored_chat is not None
        assert stored_chat.document_id == document_id
        assert stored_chat.question == "What supports local analysis?"
        assert stored_chat.answer == payload["answer"]
        assert stored_chat.provider_mode == "local"
    database_engine.dispose()


@pytest.mark.anyio
async def test_chat_with_document_route_returns_source_chunk_metadata(
    document_api_client: httpx.AsyncClient,
    document_api_settings: Settings,
) -> None:
    document_id = _create_analysis_ready_document(document_api_settings)

    async with document_api_client as client:
        response = await client.post(
            f"/api/documents/{document_id}/chat",
            json={"question": "What supports local analysis?", "top_k": 2},
        )

    assert response.status_code == 201
    source_chunk = response.json()["source_chunks"][0]
    assert source_chunk["chunk_id"] > 0
    assert source_chunk["chunk_index"] == 0
    assert source_chunk["section_name"] == "Introduction"
    assert source_chunk["page_start"] == 1
    assert source_chunk["page_end"] == 1
    assert source_chunk["score"] > 0
    assert source_chunk["snippet"] == "Retrieval retrieval supports local analysis."


@pytest.mark.anyio
async def test_chat_with_document_route_says_when_answer_not_found(
    document_api_client: httpx.AsyncClient,
    document_api_settings: Settings,
) -> None:
    document_id = _create_analysis_ready_document(document_api_settings)

    async with document_api_client as client:
        response = await client.post(
            f"/api/documents/{document_id}/chat",
            json={"question": "What quantum model was used?", "top_k": 2},
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["answer_found"] is False
    assert payload["answer"].startswith("I could not find the answer")
    assert payload["source_chunks"] == []


@pytest.mark.anyio
async def test_chat_with_document_route_stores_history_when_answer_not_found(
    document_api_client: httpx.AsyncClient,
    document_api_settings: Settings,
) -> None:
    document_id = _create_analysis_ready_document(document_api_settings)

    async with document_api_client as client:
        response = await client.post(
            f"/api/documents/{document_id}/chat",
            json={"question": "What quantum model was used?", "top_k": 2},
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["answer_found"] is False

    database_engine = create_database_engine(document_api_settings)
    session_factory = get_session_factory(database_engine)
    with session_factory() as session:
        stored_chat = session.scalar(
            select(ChatHistory).where(ChatHistory.id == payload["chat_id"])
        )
        assert stored_chat is not None
        assert stored_chat.document_id == document_id
        assert stored_chat.question == "What quantum model was used?"
        assert stored_chat.answer == payload["answer"]
        assert stored_chat.provider_mode == "local"
    database_engine.dispose()


@pytest.mark.anyio
async def test_chat_with_document_route_returns_404_for_missing_document(
    document_api_client: httpx.AsyncClient,
) -> None:
    async with document_api_client as client:
        response = await client.post(
            "/api/documents/999/chat",
            json={"question": "What did the study find?"},
        )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Document not found. Upload a document or use an existing document ID."
    )


@pytest.mark.anyio
async def test_chat_with_document_route_validates_document_id(
    document_api_client: httpx.AsyncClient,
) -> None:
    async with document_api_client as client:
        response = await client.post(
            "/api/documents/0/chat",
            json={"question": "What did the study find?"},
        )

    assert response.status_code == 422
    assert response.json()["detail"] == "Document ID must be a positive integer."


@pytest.mark.anyio
async def test_chat_with_document_route_validates_question_and_top_k(
    document_api_client: httpx.AsyncClient,
    document_api_settings: Settings,
) -> None:
    document_id = _create_analysis_ready_document(document_api_settings)

    async with document_api_client as client:
        blank_question_response = await client.post(
            f"/api/documents/{document_id}/chat",
            json={"question": "   "},
        )
        invalid_top_k_response = await client.post(
            f"/api/documents/{document_id}/chat",
            json={"question": "What did retrieval improve?", "top_k": 0},
        )

    assert blank_question_response.status_code == 422
    assert invalid_top_k_response.status_code == 422


@pytest.mark.anyio
async def test_get_document_local_overview_analysis_route_returns_404_when_missing(
    document_api_client: httpx.AsyncClient,
    document_api_settings: Settings,
) -> None:
    document_id = _create_analysis_ready_document(document_api_settings)

    async with document_api_client as client:
        response = await client.get(f"/api/documents/{document_id}/analysis/local-overview")

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Local overview analysis not found. Trigger local analysis first."
    )


@pytest.mark.anyio
async def test_create_document_local_overview_analysis_route_requires_cleaned_text(
    document_api_client: httpx.AsyncClient,
    document_api_settings: Settings,
) -> None:
    document_id = _create_document_metadata(document_api_settings, status="stored")

    async with document_api_client as client:
        response = await client.post(f"/api/documents/{document_id}/analysis/local-overview")

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Cleaned text is not available. Upload and process the document first."
    )


@pytest.mark.anyio
async def test_create_document_local_overview_analysis_route_returns_404_for_missing_document(
    document_api_client: httpx.AsyncClient,
) -> None:
    async with document_api_client as client:
        response = await client.post("/api/documents/999/analysis/local-overview")

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Document not found. Upload a document or use an existing document ID."
    )


@pytest.mark.anyio
async def test_create_research_info_analysis_route_persists_local_analysis(
    document_api_client: httpx.AsyncClient,
    document_api_settings: Settings,
) -> None:
    document_id = _create_research_info_ready_document(document_api_settings)

    async with document_api_client as client:
        response = await client.post(f"/api/analysis/{document_id}/research-info")

    assert response.status_code == 201
    payload = response.json()
    assert payload["document_id"] == document_id
    assert payload["analysis_type"] == "research_info_local"
    assert payload["title"] == "Local research information extraction"
    assert payload["provider_mode"] == "local"
    assert payload["output_json"]["document_id"] == document_id
    assert payload["output_json"]["filename"] == "research-info-ready.pdf"
    assert "lack source-grounded review tools" in (
        payload["output_json"]["fields"]["research_problem"]["extracted_text"]
    )
    assert payload["output_json"]["fields"]["research_problem"]["source_section"] == (
        "Introduction"
    )
    assert payload["output_json"]["fields"]["research_problem"]["confidence"] > 0
    assert "larger datasets" in (payload["output_json"]["fields"]["future_work"]["extracted_text"])

    database_engine = create_database_engine(document_api_settings)
    session_factory = get_session_factory(database_engine)
    with session_factory() as session:
        stored_analysis = session.scalar(select(Analysis).where(Analysis.id == payload["id"]))
        assert stored_analysis is not None
        assert stored_analysis.analysis_type == "research_info_local"
        assert stored_analysis.provider_mode == "local"
        stored_payload = json.loads(stored_analysis.content)
        assert stored_payload == payload["output_json"]
    database_engine.dispose()


@pytest.mark.anyio
async def test_create_research_info_analysis_route_requires_cleaned_text(
    document_api_client: httpx.AsyncClient,
    document_api_settings: Settings,
) -> None:
    document_id = _create_document_metadata(document_api_settings, status="stored")

    async with document_api_client as client:
        response = await client.post(f"/api/analysis/{document_id}/research-info")

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Cleaned text is not available. Upload and process the document first."
    )


@pytest.mark.anyio
async def test_create_research_info_analysis_route_returns_404_for_missing_document(
    document_api_client: httpx.AsyncClient,
) -> None:
    async with document_api_client as client:
        response = await client.post("/api/analysis/999/research-info")

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Document not found. Upload a document or use an existing document ID."
    )


@pytest.mark.anyio
async def test_create_research_info_analysis_route_returns_invalid_id_error(
    document_api_client: httpx.AsyncClient,
) -> None:
    async with document_api_client as client:
        response = await client.post("/api/analysis/0/research-info")

    assert response.status_code == 422
    assert response.json()["detail"] == "Document ID must be a positive integer."


@pytest.mark.anyio
async def test_upload_document_route_extracts_valid_pdf_metadata(
    document_api_client: httpx.AsyncClient,
    document_api_settings: Settings,
) -> None:
    project_id = _create_project(document_api_settings)
    pdf_content = _pdf_bytes(
        "Local extraction works with enough academic text for the deterministic threshold."
    )

    async with document_api_client as client:
        response = await client.post(
            f"/api/projects/{project_id}/documents",
            files={"file": ("paper.pdf", pdf_content, "application/pdf")},
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["page_count"] == 1
    assert payload["word_count"] == 11
    assert payload["status"] == "processed"
    assert payload["extraction_error"] is None
    assert "extracted_text_path" not in payload
    assert "cleaned_text_path" not in payload

    saved_pdf_files = list(document_api_settings.upload_dir.rglob("*.pdf"))
    extracted_text_files = list(document_api_settings.upload_dir.rglob("*.extracted.txt"))
    cleaned_text_files = list(document_api_settings.upload_dir.rglob("*.cleaned.txt"))

    assert len(saved_pdf_files) == 1
    assert saved_pdf_files[0].read_bytes() == pdf_content
    assert len(extracted_text_files) == 1
    assert len(cleaned_text_files) == 1
    assert "Local extraction works" in extracted_text_files[0].read_text(encoding="utf-8")
    assert "Local extraction works" in cleaned_text_files[0].read_text(encoding="utf-8")

    database_engine = create_database_engine(document_api_settings)
    session_factory = get_session_factory(database_engine)
    with session_factory() as session:
        document = session.get(Document, payload["id"])
        assert document is not None
        assert document.extracted_text_path == str(extracted_text_files[0])
        assert document.cleaned_text_path == str(cleaned_text_files[0])
        assert document.cleaning_warnings is None
    database_engine.dispose()


@pytest.mark.anyio
async def test_upload_document_route_marks_low_text_pdf_as_ocr_needed(
    document_api_client: httpx.AsyncClient,
    document_api_settings: Settings,
) -> None:
    project_id = _create_project(document_api_settings)
    pdf_content = _pdf_bytes("Title")

    async with document_api_client as client:
        response = await client.post(
            f"/api/projects/{project_id}/documents",
            files={"file": ("scanned.pdf", pdf_content, "application/pdf")},
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["page_count"] == 1
    assert payload["word_count"] == 1
    assert payload["status"] == "ocr_needed"
    assert "OCR" in payload["extraction_error"]
    assert len(list(document_api_settings.upload_dir.rglob("*.cleaned.txt"))) == 1


@pytest.mark.anyio
async def test_upload_document_route_marks_empty_pdf_as_ocr_needed(
    document_api_client: httpx.AsyncClient,
    document_api_settings: Settings,
) -> None:
    project_id = _create_project(document_api_settings)
    pdf_content = _pdf_bytes("")

    async with document_api_client as client:
        response = await client.post(
            f"/api/projects/{project_id}/documents",
            files={"file": ("empty.pdf", pdf_content, "application/pdf")},
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["page_count"] == 1
    assert payload["word_count"] == 0
    assert payload["status"] == "ocr_needed"
    assert "Very little extractable text" in payload["extraction_error"]


@pytest.mark.anyio
async def test_upload_document_route_uses_mocked_normal_extraction(
    document_api_client: httpx.AsyncClient,
    document_api_settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_id = _create_project(document_api_settings)

    def fake_extract_pdf_text(_: Path) -> ExtractedPDF:
        return ExtractedPDF(
            page_count=2,
            metadata={"title": "Mocked"},
            page_texts=[
                "This mocked page contains enough words for extraction success.",
                "This second mocked page also contributes additional words.",
            ],
        )

    monkeypatch.setattr("backend.app.api.routes_documents.extract_pdf_text", fake_extract_pdf_text)

    async with document_api_client as client:
        response = await client.post(
            f"/api/projects/{project_id}/documents",
            files={
                "file": (
                    "mocked.pdf",
                    b"fake bytes are enough with mocked extraction",
                    "application/pdf",
                )
            },
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["page_count"] == 2
    assert payload["word_count"] == 17
    assert payload["status"] == "processed"
    assert payload["extraction_error"] is None


@pytest.mark.anyio
async def test_upload_document_route_stores_section_detection_analysis(
    document_api_client: httpx.AsyncClient,
    document_api_settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_id = _create_project(document_api_settings)

    def fake_extract_pdf_text(_: Path) -> ExtractedPDF:
        return ExtractedPDF(
            page_count=4,
            metadata={"title": "Structured"},
            page_texts=[
                "Structured Thesis Assistant\n\n"
                "Abstract\n"
                "This abstract has enough words for section detection and upload success.\n\n"
                "Introduction\n"
                "This introduction explains the local research workflow.\n\n"
                "References\n"
                "Smith, J. Local Research."
            ],
        )

    monkeypatch.setattr("backend.app.api.routes_documents.extract_pdf_text", fake_extract_pdf_text)

    async with document_api_client as client:
        response = await client.post(
            f"/api/projects/{project_id}/documents",
            files={"file": ("structured.pdf", b"fake bytes", "application/pdf")},
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "processed"

    database_engine = create_database_engine(document_api_settings)
    session_factory = get_session_factory(database_engine)
    with session_factory() as session:
        analyses = session.query(Analysis).filter_by(document_id=payload["id"]).all()
        assert len(analyses) == 1
        analysis = analyses[0]
        assert analysis.analysis_type == "section_detection"
        section_payload = json.loads(analysis.content)
        assert [section["section_type"] for section in section_payload] == [
            "title",
            "abstract",
            "introduction",
            "references",
        ]
        assert section_payload[1]["detected_heading"] == "Abstract"
        assert section_payload[1]["confidence"] == 0.95
        chunks = session.query(Chunk).filter_by(document_id=payload["id"]).all()
        assert len(chunks) == 4
        assert [chunk.chunk_index for chunk in chunks] == [0, 1, 2, 3]
        assert [chunk.section_name for chunk in chunks] == [
            "Title",
            "Abstract",
            "Introduction",
            "References",
        ]
    database_engine.dispose()


@pytest.mark.anyio
async def test_upload_document_route_uses_mocked_empty_text_detection(
    document_api_client: httpx.AsyncClient,
    document_api_settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_id = _create_project(document_api_settings)

    def fake_extract_pdf_text(_: Path) -> ExtractedPDF:
        return ExtractedPDF(page_count=3, metadata={}, page_texts=["", " ", ""])

    monkeypatch.setattr("backend.app.api.routes_documents.extract_pdf_text", fake_extract_pdf_text)

    async with document_api_client as client:
        response = await client.post(
            f"/api/projects/{project_id}/documents",
            files={"file": ("empty-mocked.pdf", b"fake bytes", "application/pdf")},
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["page_count"] == 3
    assert payload["word_count"] == 0
    assert payload["status"] == "ocr_needed"
    assert "OCR" in payload["extraction_error"]


@pytest.mark.anyio
async def test_upload_document_route_reports_text_artifact_storage_failure(
    document_api_client: httpx.AsyncClient,
    document_api_settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_id = _create_project(document_api_settings)

    def fake_extract_pdf_text(_: Path) -> ExtractedPDF:
        return ExtractedPDF(
            page_count=1,
            metadata={},
            page_texts=["This document has enough words to pass the extraction threshold."],
        )

    def fail_save_text_processing_artifacts(*args, **kwargs):
        raise DocumentStorageError("text artifact disk unavailable")

    monkeypatch.setattr("backend.app.api.routes_documents.extract_pdf_text", fake_extract_pdf_text)
    monkeypatch.setattr(
        "backend.app.api.routes_documents.save_text_processing_artifacts",
        fail_save_text_processing_artifacts,
    )

    async with document_api_client as client:
        response = await client.post(
            f"/api/projects/{project_id}/documents",
            files={"file": ("paper.pdf", b"fake pdf bytes", "application/pdf")},
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["page_count"] == 1
    assert payload["word_count"] == 10
    assert payload["status"] == "text_processing_failed"
    assert "text artifact disk unavailable" in payload["extraction_error"]


@pytest.mark.anyio
async def test_upload_document_route_reports_section_analysis_storage_failure(
    document_api_client: httpx.AsyncClient,
    document_api_settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_id = _create_project(document_api_settings)

    def fake_extract_pdf_text(_: Path) -> ExtractedPDF:
        return ExtractedPDF(
            page_count=1,
            metadata={},
            page_texts=["Abstract\nThis document has enough words for local processing success."],
        )

    def fail_create_section_detection_analysis(*args, **kwargs):
        raise DocumentProcessingError("section analysis unavailable")

    monkeypatch.setattr("backend.app.api.routes_documents.extract_pdf_text", fake_extract_pdf_text)
    monkeypatch.setattr(
        "backend.app.api.routes_documents.create_section_detection_analysis",
        fail_create_section_detection_analysis,
    )

    async with document_api_client as client:
        response = await client.post(
            f"/api/projects/{project_id}/documents",
            files={"file": ("paper.pdf", b"fake pdf bytes", "application/pdf")},
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "section_detection_failed"
    assert "section analysis unavailable" in payload["extraction_error"]


@pytest.mark.anyio
async def test_upload_document_route_reports_chunk_storage_failure(
    document_api_client: httpx.AsyncClient,
    document_api_settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_id = _create_project(document_api_settings)

    def fake_extract_pdf_text(_: Path) -> ExtractedPDF:
        return ExtractedPDF(
            page_count=2,
            metadata={},
            page_texts=[
                "Abstract\n"
                "This document has enough words for section detection and chunk storage."
            ],
        )

    def fail_replace_document_chunks(*args, **kwargs):
        raise ChunkPersistenceError("chunk database unavailable")

    monkeypatch.setattr("backend.app.api.routes_documents.extract_pdf_text", fake_extract_pdf_text)
    monkeypatch.setattr(
        "backend.app.api.routes_documents.replace_document_chunks",
        fail_replace_document_chunks,
    )

    async with document_api_client as client:
        response = await client.post(
            f"/api/projects/{project_id}/documents",
            files={"file": ("paper.pdf", b"fake pdf bytes", "application/pdf")},
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "chunking_failed"
    assert "chunk database unavailable" in payload["extraction_error"]


@pytest.mark.anyio
async def test_upload_document_route_accepts_uppercase_pdf_extension_and_x_pdf_type(
    document_api_client: httpx.AsyncClient,
    document_api_settings: Settings,
) -> None:
    project_id = _create_project(document_api_settings)

    async with document_api_client as client:
        response = await client.post(
            f"/api/projects/{project_id}/documents",
            files={"file": ("Paper.PDF", b"tiny fake pdf", "application/x-pdf")},
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["original_filename"] == "Paper.PDF"
    assert payload["mime_type"] == "application/x-pdf"
    assert payload["page_count"] is None
    assert payload["word_count"] is None
    assert payload["status"] == "extraction_failed"
    assert payload["extraction_error"]


@pytest.mark.anyio
async def test_upload_document_route_saves_small_fake_file_when_extraction_fails(
    document_api_client: httpx.AsyncClient,
    document_api_settings: Settings,
) -> None:
    project_id = _create_project(document_api_settings)
    fake_file_content = b"not a parsed pdf"

    async with document_api_client as client:
        response = await client.post(
            f"/api/projects/{project_id}/documents",
            files={"file": ("../Unsafe File Name!.pdf", fake_file_content, "application/pdf")},
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["original_filename"] == "../Unsafe File Name!.pdf"
    assert payload["page_count"] is None
    assert payload["word_count"] is None
    assert payload["status"] == "extraction_failed"
    assert payload["extraction_error"]

    saved_files = list(document_api_settings.upload_dir.rglob("*.pdf"))
    assert len(saved_files) == 1
    assert saved_files[0].read_bytes() == fake_file_content
    assert "Unsafe_File_Name.pdf" in saved_files[0].name

    database_engine = create_database_engine(document_api_settings)
    session_factory = get_session_factory(database_engine)
    with session_factory() as session:
        document = session.get(Document, payload["id"])
        assert document is not None
        assert document.page_count is None
        assert document.word_count is None
        assert document.status == "extraction_failed"
        assert document.extraction_error is not None
        assert document.stored_filename.endswith("_Unsafe_File_Name.pdf")
        assert "file_path" not in payload
        assert "stored_filename" not in payload
    database_engine.dispose()


@pytest.mark.anyio
async def test_upload_document_route_returns_404_for_missing_project(
    document_api_client: httpx.AsyncClient,
) -> None:
    async with document_api_client as client:
        response = await client.post(
            "/api/projects/999/documents",
            files={"file": ("paper.pdf", b"%PDF-1.4", "application/pdf")},
        )

    assert response.status_code == 404
    assert response.json()["detail"] == "Project not found."


@pytest.mark.anyio
async def test_upload_document_route_rejects_non_pdf_extension(
    document_api_client: httpx.AsyncClient,
    document_api_settings: Settings,
) -> None:
    project_id = _create_project(document_api_settings)

    async with document_api_client as client:
        response = await client.post(
            f"/api/projects/{project_id}/documents",
            files={"file": ("notes.txt", b"text", "application/pdf")},
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Only PDF files are supported."


@pytest.mark.anyio
async def test_upload_document_route_rejects_wrong_content_type(
    document_api_client: httpx.AsyncClient,
    document_api_settings: Settings,
) -> None:
    project_id = _create_project(document_api_settings)

    async with document_api_client as client:
        response = await client.post(
            f"/api/projects/{project_id}/documents",
            files={"file": ("paper.pdf", b"fake", "text/plain")},
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Uploaded file content type must be application/pdf."


@pytest.mark.anyio
async def test_upload_document_route_rejects_oversized_file(
    document_api_client: httpx.AsyncClient,
    document_api_settings: Settings,
) -> None:
    project_id = _create_project(document_api_settings)

    async with document_api_client as client:
        response = await client.post(
            f"/api/projects/{project_id}/documents",
            files={
                "file": (
                    "paper.pdf",
                    b"x" * (document_api_settings.max_upload_file_size_bytes + 1),
                    "application/pdf",
                )
            },
        )

    assert response.status_code == 413
    assert response.json()["detail"] == "Uploaded file exceeds the configured size limit."


@pytest.mark.anyio
async def test_upload_document_route_accepts_file_at_configured_size_limit(
    document_api_client: httpx.AsyncClient,
    document_api_settings: Settings,
) -> None:
    project_id = _create_project(document_api_settings)

    async with document_api_client as client:
        response = await client.post(
            f"/api/projects/{project_id}/documents",
            files={
                "file": (
                    "paper.pdf",
                    b"x" * document_api_settings.max_upload_file_size_bytes,
                    "application/pdf",
                )
            },
        )

    assert response.status_code == 201
    assert response.json()["file_size_bytes"] == document_api_settings.max_upload_file_size_bytes


@pytest.mark.anyio
async def test_upload_document_route_requires_file_field(
    document_api_client: httpx.AsyncClient,
    document_api_settings: Settings,
) -> None:
    project_id = _create_project(document_api_settings)

    async with document_api_client as client:
        response = await client.post(f"/api/projects/{project_id}/documents")

    assert response.status_code == 422


@pytest.mark.anyio
async def test_upload_document_route_handles_storage_failure(
    document_api_client: httpx.AsyncClient,
    document_api_settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_id = _create_project(document_api_settings)

    def fail_save(*args, **kwargs):
        raise DocumentStorageError("disk unavailable")

    monkeypatch.setattr("backend.app.api.routes_documents.save_uploaded_file", fail_save)

    async with document_api_client as client:
        response = await client.post(
            f"/api/projects/{project_id}/documents",
            files={"file": ("paper.pdf", b"%PDF-1.4", "application/pdf")},
        )

    assert response.status_code == 500
    assert response.json()["detail"] == "Could not save uploaded document."
