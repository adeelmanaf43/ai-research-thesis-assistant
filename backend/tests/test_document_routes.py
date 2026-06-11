from collections.abc import Generator
from pathlib import Path

import httpx
import pytest
from sqlalchemy.orm import Session

from backend.app.core.config import Settings, get_settings
from backend.app.core.database import (
    create_database_engine,
    get_db,
    get_session_factory,
    init_database,
)
from backend.app.main import create_app
from backend.app.models.document import Document
from backend.app.schemas.project import ProjectCreate
from backend.app.services.document_service import DocumentStorageError
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
        max_upload_file_size_bytes=20,
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
    assert payload["status"] == "stored"
    assert "file_path" not in payload
    assert "stored_filename" not in payload
    assert len(list(document_api_settings.upload_dir.rglob("*.pdf"))) == 1


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


@pytest.mark.anyio
async def test_upload_document_route_saves_small_fake_file_without_pdf_extraction(
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
            files={"file": ("paper.pdf", b"x" * 21, "application/pdf")},
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
