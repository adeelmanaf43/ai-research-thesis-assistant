from pathlib import Path

from sqlalchemy import select

from backend.app.core.config import Settings
from backend.app.core.database import create_database_engine, get_session_factory, init_database
from backend.app.models.project import Project
from backend.app.schemas.project import ProjectCreate, ProjectUpdate
from backend.app.services.project_service import (
    create_project,
    delete_project,
    get_project_by_id,
    list_projects,
    update_project,
)


def _session_factory(workspace_tmp_path: Path):
    database_path = workspace_tmp_path / "project_service.db"
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


def test_create_project_persists_project_without_login(workspace_tmp_path: Path) -> None:
    session_factory, database_engine = _session_factory(workspace_tmp_path)

    with session_factory() as session:
        project = create_project(
            session,
            ProjectCreate(name="Thesis workspace", description="Local MVP"),
        )

        assert project.id is not None
        assert project.user_id is None
        assert project.name == "Thesis workspace"
        assert project.description == "Local MVP"

    database_engine.dispose()


def test_list_projects_returns_newest_first_and_can_filter_by_user(
    workspace_tmp_path: Path,
) -> None:
    session_factory, database_engine = _session_factory(workspace_tmp_path)

    with session_factory() as session:
        create_project(session, ProjectCreate(name="Shared project"))
        user_project = create_project(session, ProjectCreate(name="User project"), user_id=7)

        all_projects = list_projects(session)
        user_projects = list_projects(session, user_id=7)

        assert [project.name for project in all_projects] == ["User project", "Shared project"]
        assert user_projects == [user_project]

    database_engine.dispose()


def test_get_project_by_id_respects_optional_user_filter(workspace_tmp_path: Path) -> None:
    session_factory, database_engine = _session_factory(workspace_tmp_path)

    with session_factory() as session:
        project = create_project(session, ProjectCreate(name="Owned project"), user_id=3)

        assert get_project_by_id(session, project.id) == project
        assert get_project_by_id(session, project.id, user_id=3) == project
        assert get_project_by_id(session, project.id, user_id=99) is None
        assert get_project_by_id(session, 9999) is None

    database_engine.dispose()


def test_update_project_applies_partial_changes(workspace_tmp_path: Path) -> None:
    session_factory, database_engine = _session_factory(workspace_tmp_path)

    with session_factory() as session:
        project = create_project(
            session,
            ProjectCreate(name="Draft name", description="Original description"),
        )

        updated = update_project(session, project, ProjectUpdate(name="Final name"))

        assert updated.id == project.id
        assert updated.name == "Final name"
        assert updated.description == "Original description"

    database_engine.dispose()


def test_update_project_can_clear_description(workspace_tmp_path: Path) -> None:
    session_factory, database_engine = _session_factory(workspace_tmp_path)

    with session_factory() as session:
        project = create_project(
            session,
            ProjectCreate(name="Project", description="Remove me"),
        )

        updated = update_project(session, project, ProjectUpdate(description=None))

        assert updated.description is None

    database_engine.dispose()


def test_delete_project_removes_project(workspace_tmp_path: Path) -> None:
    session_factory, database_engine = _session_factory(workspace_tmp_path)

    with session_factory() as session:
        project = create_project(session, ProjectCreate(name="Temporary project"))
        project_id = project.id

        delete_project(session, project)
        remaining = session.scalars(select(Project).where(Project.id == project_id)).first()

        assert remaining is None

    database_engine.dispose()
