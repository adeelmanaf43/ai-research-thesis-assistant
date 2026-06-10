from pathlib import Path

from backend.app.core.config import Settings
from backend.app.core.database import get_connection, sqlite_path_from_url


def test_sqlite_path_from_url_accepts_sqlite_url() -> None:
    assert sqlite_path_from_url("sqlite:///data/app.db") == Path("data/app.db")


def test_sqlite_path_from_url_rejects_non_sqlite_url() -> None:
    try:
        sqlite_path_from_url("postgresql://localhost/app")
    except ValueError as exc:
        assert "Only sqlite" in str(exc)
    else:
        raise AssertionError("Expected ValueError for non-sqlite database URL")


def test_get_connection_opens_sqlite_database(workspace_tmp_path: Path) -> None:
    database_path = workspace_tmp_path / "app.db"
    settings = Settings(
        app_name="Test App",
        app_version="0.1.0",
        environment="test",
        data_dir=workspace_tmp_path,
        upload_dir=workspace_tmp_path / "uploads",
        database_url=f"sqlite:///{database_path}",
    )

    with get_connection(settings) as connection:
        result = connection.execute("select 1 as value").fetchone()

    assert result["value"] == 1
    assert database_path.exists()
