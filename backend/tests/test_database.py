from pathlib import Path

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from backend.app.core.config import Settings
from backend.app.core.database import (
    Base,
    create_database_engine,
    get_db,
    get_session_factory,
    init_database,
    sqlite_path_from_url,
)


def test_sqlite_path_from_url_accepts_sqlite_url() -> None:
    assert sqlite_path_from_url("sqlite:///data/app.db") == Path("data/app.db")


def test_sqlite_path_from_url_rejects_non_sqlite_url() -> None:
    try:
        sqlite_path_from_url("postgresql://localhost/app")
    except ValueError as exc:
        assert "Only sqlite" in str(exc)
    else:
        raise AssertionError("Expected ValueError for non-sqlite database URL")


def test_create_database_engine_opens_sqlite_database(workspace_tmp_path: Path) -> None:
    database_path = workspace_tmp_path / "app.db"
    settings = Settings(
        app_name="Test App",
        app_version="0.1.0",
        environment="test",
        data_dir=workspace_tmp_path,
        upload_dir=workspace_tmp_path / "uploads",
        export_dir=workspace_tmp_path / "exports",
        database_url=f"sqlite:///{database_path}",
        provider_mode="local",
    )

    database_engine = create_database_engine(settings)
    session_factory = get_session_factory(database_engine)

    with session_factory() as session:
        result = session.execute(text("select 1 as value")).scalar_one()

    database_engine.dispose()

    assert result == 1
    assert database_path.exists()


def test_get_db_yields_sqlalchemy_session() -> None:
    database_dependency = get_db()
    session = next(database_dependency)

    try:
        assert isinstance(session, Session)
    finally:
        try:
            next(database_dependency)
        except StopIteration:
            pass


def test_init_database_creates_base_model_tables(workspace_tmp_path: Path) -> None:
    database_path = workspace_tmp_path / "base_schema.db"
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
    table_names = inspect(database_engine).get_table_names()

    database_engine.dispose()

    assert set(Base.metadata.tables) >= {
        "analyses",
        "chat_history",
        "chunks",
        "documents",
        "projects",
        "users",
    }
    assert set(table_names) == {
        "analyses",
        "chat_history",
        "chunks",
        "documents",
        "projects",
        "users",
    }
