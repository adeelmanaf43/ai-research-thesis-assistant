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
from backend.app.models.chunk import Chunk
from backend.app.models.document import Document
from backend.app.services.document_extraction import ExtractedPDF


@pytest.fixture
def integration_settings(workspace_tmp_path: Path) -> Settings:
    return Settings(
        app_name="Test App",
        app_version="0.1.0",
        environment="test",
        data_dir=workspace_tmp_path,
        upload_dir=workspace_tmp_path / "uploads",
        export_dir=workspace_tmp_path / "exports",
        database_url=f"sqlite:///{(workspace_tmp_path / 'week2_integration.db').as_posix()}",
        provider_mode="local",
        max_upload_file_size_bytes=250_000,
    )


@pytest.fixture
def integration_client(integration_settings: Settings):
    database_engine = create_database_engine(integration_settings)
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
    test_app.dependency_overrides[get_settings] = lambda: integration_settings
    transport = httpx.ASGITransport(app=test_app)

    try:
        yield httpx.AsyncClient(transport=transport, base_url="http://testserver")
    finally:
        test_app.dependency_overrides.clear()
        database_engine.dispose()


def _structured_research_pdf_bytes() -> bytes:
    lines = [
        "Integration Research Paper",
        "Abstract",
        "This abstract validates local extraction and cleaning.",
        "It also checks chunk storage and overview responses.",
        "Introduction",
        "The test uploads a generated text based PDF through the public API.",
        "It checks the complete local processing workflow.",
        "Methodology",
        "The system saves the original PDF and extracts readable text.",
        "It cleans text detects sections creates chunks and stores SQLite metadata.",
        "Conclusion",
        "The document should become processed after chunk storage.",
        "The overview endpoint should return safe user facing details.",
    ]

    document = fitz.open()
    page = document.new_page()
    y_position = 72
    for line in lines:
        page.insert_text((72, y_position), line, fontsize=11)
        y_position += 18

    pdf_content = document.tobytes()
    document.close()
    return pdf_content


def _words(count: int, prefix: str = "word") -> str:
    return " ".join(f"{prefix}{index}" for index in range(count))


@pytest.mark.anyio
async def test_week2_upload_processing_and_overview_integration(
    integration_client: httpx.AsyncClient,
    integration_settings: Settings,
) -> None:
    async with integration_client as client:
        project_response = await client.post(
            "/api/projects",
            json={
                "name": "Integration thesis project",
                "description": "Week 2 processing validation",
            },
        )
        project_id = project_response.json()["id"]

        upload_response = await client.post(
            f"/api/projects/{project_id}/documents",
            files={
                "file": (
                    "integration-paper.pdf",
                    _structured_research_pdf_bytes(),
                    "application/pdf",
                )
            },
        )

        assert upload_response.status_code == 201
        upload_payload = upload_response.json()
        document_id = upload_payload["id"]
        assert upload_payload["project_id"] == project_id
        assert upload_payload["original_filename"] == "integration-paper.pdf"
        assert upload_payload["status"] == "processed"
        assert upload_payload["page_count"] == 1
        assert upload_payload["word_count"] >= 50
        assert upload_payload["extraction_error"] is None

        list_response = await client.get(f"/api/projects/{project_id}/documents")
        assert list_response.status_code == 200
        assert [document["id"] for document in list_response.json()] == [document_id]

        overview_response = await client.get(f"/api/documents/{document_id}/overview")
        assert overview_response.status_code == 200
        overview_payload = overview_response.json()

    detected_section_names = {
        section["section_name"] for section in overview_payload["detected_sections"]
    }
    assert {"Title", "Abstract", "Introduction", "Methodology", "Conclusion"}.issubset(
        detected_section_names
    )
    assert overview_payload["document_id"] == document_id
    assert overview_payload["filename"] == "integration-paper.pdf"
    assert overview_payload["status"] == "processed"
    assert overview_payload["chunk_count"] >= 4
    assert overview_payload["extraction_warnings"] == []
    assert overview_payload["processing_summary"]["is_complete"] is True
    assert overview_payload["processing_summary"]["requires_attention"] is False

    database_engine = create_database_engine(integration_settings)
    session_factory = get_session_factory(database_engine)
    with session_factory() as session:
        document = session.get(Document, document_id)
        assert document is not None
        assert document.status == "processed"
        assert document.extracted_text_path is not None
        assert document.cleaned_text_path is not None
        assert Path(document.file_path).exists()
        assert Path(document.extracted_text_path).exists()
        assert Path(document.cleaned_text_path).exists()

        analysis = session.scalars(
            select(Analysis).where(
                Analysis.document_id == document_id,
                Analysis.analysis_type == "section_detection",
            )
        ).one()
        assert analysis.provider_mode == "local"
        assert "Abstract" in analysis.content

        chunks = list(
            session.scalars(
                select(Chunk)
                .where(Chunk.document_id == document_id)
                .order_by(Chunk.chunk_index.asc())
            )
        )
        assert len(chunks) == overview_payload["chunk_count"]
        assert [chunk.chunk_index for chunk in chunks] == list(range(len(chunks)))
        assert {chunk.section_name for chunk in chunks}.issuperset(
            {"Abstract", "Introduction", "Methodology", "Conclusion"}
        )

    database_engine.dispose()


@pytest.mark.anyio
async def test_duplicate_uploads_with_same_filename_create_separate_processed_documents(
    integration_client: httpx.AsyncClient,
) -> None:
    pdf_content = _structured_research_pdf_bytes()

    async with integration_client as client:
        project_response = await client.post(
            "/api/projects",
            json={"name": "Duplicate upload project"},
        )
        project_id = project_response.json()["id"]

        first_upload = await client.post(
            f"/api/projects/{project_id}/documents",
            files={"file": ("same-name.pdf", pdf_content, "application/pdf")},
        )
        second_upload = await client.post(
            f"/api/projects/{project_id}/documents",
            files={"file": ("same-name.pdf", pdf_content, "application/pdf")},
        )
        list_response = await client.get(f"/api/projects/{project_id}/documents")

    assert first_upload.status_code == 201
    assert second_upload.status_code == 201
    first_payload = first_upload.json()
    second_payload = second_upload.json()
    assert first_payload["id"] != second_payload["id"]
    assert first_payload["status"] == "processed"
    assert second_payload["status"] == "processed"
    assert first_payload["original_filename"] == "same-name.pdf"
    assert second_payload["original_filename"] == "same-name.pdf"
    assert [document["id"] for document in list_response.json()] == [
        second_payload["id"],
        first_payload["id"],
    ]


@pytest.mark.anyio
async def test_long_document_upload_processing_stores_multiple_chunks(
    integration_client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    long_abstract = _words(1_300, "abstract")
    long_methodology = _words(1_300, "methodology")

    def fake_extract_pdf_text(_: Path) -> ExtractedPDF:
        return ExtractedPDF(
            page_count=12,
            metadata={"title": "Long integration paper"},
            page_texts=[
                (
                    "Long Integration Paper\n\n"
                    f"Abstract\n{long_abstract}.\n\n"
                    f"Methodology\n{long_methodology}.\n\n"
                    "Conclusion\nThis document validates long local processing."
                )
            ],
        )

    monkeypatch.setattr("backend.app.api.routes_documents.extract_pdf_text", fake_extract_pdf_text)

    async with integration_client as client:
        project_response = await client.post(
            "/api/projects",
            json={"name": "Long document project"},
        )
        project_id = project_response.json()["id"]
        upload_response = await client.post(
            f"/api/projects/{project_id}/documents",
            files={"file": ("long-paper.pdf", b"mocked pdf bytes", "application/pdf")},
        )
        document_id = upload_response.json()["id"]
        overview_response = await client.get(f"/api/documents/{document_id}/overview")

    assert upload_response.status_code == 201
    upload_payload = upload_response.json()
    assert upload_payload["status"] == "processed"
    assert upload_payload["page_count"] == 12
    assert upload_payload["word_count"] > 2_600

    overview_payload = overview_response.json()
    assert overview_response.status_code == 200
    assert overview_payload["chunk_count"] >= 4
    assert overview_payload["processing_summary"]["is_complete"] is True
    assert {
        section["section_name"] for section in overview_payload["detected_sections"]
    }.issuperset({"Title", "Abstract", "Methodology", "Conclusion"})
