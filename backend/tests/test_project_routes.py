from collections.abc import Generator
from pathlib import Path

import httpx
import pytest
from sqlalchemy.orm import Session

from backend.app.core.config import Settings
from backend.app.core.database import (
    create_database_engine,
    get_db,
    get_session_factory,
    init_database,
)
from backend.app.main import create_app


@pytest.fixture
def project_api_database_path(workspace_tmp_path: Path) -> Path:
    return workspace_tmp_path / "project_routes.db"


def _session_factory(workspace_tmp_path: Path, database_path: Path):
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
    return get_session_factory(database_engine), database_engine


@pytest.fixture
def project_api_client(workspace_tmp_path: Path, project_api_database_path: Path):
    session_factory, database_engine = _session_factory(
        workspace_tmp_path, project_api_database_path
    )
    test_app = create_app()

    def override_get_db() -> Generator[Session, None, None]:
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    test_app.dependency_overrides[get_db] = override_get_db
    transport = httpx.ASGITransport(app=test_app)

    try:
        yield httpx.AsyncClient(transport=transport, base_url="http://testserver")
    finally:
        test_app.dependency_overrides.clear()
        database_engine.dispose()


@pytest.mark.anyio
async def test_create_project_route(project_api_client: httpx.AsyncClient) -> None:
    async with project_api_client as client:
        response = await client.post(
            "/api/projects",
            json={"name": "Thesis project", "description": "Local workspace"},
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["id"] == 1
    assert payload["user_id"] is None
    assert payload["name"] == "Thesis project"
    assert payload["description"] == "Local workspace"


@pytest.mark.anyio
async def test_project_routes_use_isolated_test_database(
    project_api_client: httpx.AsyncClient,
    project_api_database_path: Path,
    workspace_tmp_path: Path,
) -> None:
    async with project_api_client as client:
        response = await client.post("/api/projects", json={"name": "Isolated"})

    assert response.status_code == 201
    assert project_api_database_path.exists()
    assert workspace_tmp_path in project_api_database_path.parents


@pytest.mark.anyio
async def test_list_projects_route(project_api_client: httpx.AsyncClient) -> None:
    async with project_api_client as client:
        await client.post("/api/projects", json={"name": "First"})
        await client.post("/api/projects", json={"name": "Second"})
        response = await client.get("/api/projects")

    assert response.status_code == 200
    assert [project["name"] for project in response.json()] == ["Second", "First"]


@pytest.mark.anyio
async def test_get_project_route_returns_project(project_api_client: httpx.AsyncClient) -> None:
    async with project_api_client as client:
        created = await client.post("/api/projects", json={"name": "Find me"})
        project_id = created.json()["id"]
        response = await client.get(f"/api/projects/{project_id}")

    assert response.status_code == 200
    assert response.json()["name"] == "Find me"


@pytest.mark.anyio
async def test_update_project_route_applies_patch(project_api_client: httpx.AsyncClient) -> None:
    async with project_api_client as client:
        created = await client.post(
            "/api/projects",
            json={"name": "Draft", "description": "Keep this"},
        )
        project_id = created.json()["id"]
        response = await client.patch(f"/api/projects/{project_id}", json={"name": "Final"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "Final"
    assert payload["description"] == "Keep this"


@pytest.mark.anyio
async def test_delete_project_route_removes_project(project_api_client: httpx.AsyncClient) -> None:
    async with project_api_client as client:
        created = await client.post("/api/projects", json={"name": "Temporary"})
        project_id = created.json()["id"]
        delete_response = await client.delete(f"/api/projects/{project_id}")
        get_response = await client.get(f"/api/projects/{project_id}")

    assert delete_response.status_code == 204
    assert get_response.status_code == 404


@pytest.mark.anyio
async def test_project_routes_return_404_for_missing_project(
    project_api_client: httpx.AsyncClient,
) -> None:
    async with project_api_client as client:
        get_response = await client.get("/api/projects/999")
        patch_response = await client.patch("/api/projects/999", json={"name": "Missing"})
        delete_response = await client.delete("/api/projects/999")

    assert get_response.status_code == 404
    assert patch_response.status_code == 404
    assert delete_response.status_code == 404


@pytest.mark.anyio
async def test_project_routes_reject_empty_names(project_api_client: httpx.AsyncClient) -> None:
    async with project_api_client as client:
        create_response = await client.post("/api/projects", json={"name": "   "})
        created = await client.post("/api/projects", json={"name": "Valid"})
        patch_response = await client.patch(
            f"/api/projects/{created.json()['id']}",
            json={"name": "   "},
        )

    assert create_response.status_code == 422
    assert patch_response.status_code == 422
