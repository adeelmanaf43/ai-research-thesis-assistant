from pathlib import Path

from backend.app.core.config import Settings


def test_settings_load_defaults() -> None:
    settings = Settings.from_env()

    assert settings.app_name == "AI Research / Thesis Assistant"
    assert settings.app_version == "0.1.0"
    assert settings.environment
    assert isinstance(settings.data_dir, Path)
    assert settings.database_url.startswith("sqlite:///")


def test_settings_create_local_directories(workspace_tmp_path: Path) -> None:
    settings = Settings(
        app_name="Test App",
        app_version="0.1.0",
        environment="test",
        data_dir=workspace_tmp_path / "data",
        upload_dir=workspace_tmp_path / "data" / "uploads",
        database_url=f"sqlite:///{workspace_tmp_path / 'data' / 'app.db'}",
    )

    settings.ensure_local_directories()

    assert settings.data_dir.exists()
    assert settings.upload_dir.exists()
