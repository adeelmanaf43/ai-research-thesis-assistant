from pathlib import Path

from backend.app.core.config import Settings


def test_settings_load_defaults() -> None:
    settings = Settings.from_env()

    assert settings.app_name == "AI Research / Thesis Assistant"
    assert settings.app_version == "0.1.0"
    assert settings.environment
    assert isinstance(settings.data_dir, Path)
    assert isinstance(settings.upload_dir, Path)
    assert isinstance(settings.export_dir, Path)
    assert settings.database_url.startswith("sqlite:///")
    assert "\\" not in settings.database_url
    assert settings.provider_mode == "local"
    assert settings.max_upload_file_size_bytes == 25 * 1024 * 1024
    assert settings.data_dir.is_absolute()
    assert settings.upload_dir.is_absolute()
    assert settings.export_dir.is_absolute()


def test_settings_create_local_directories(workspace_tmp_path: Path) -> None:
    settings = Settings(
        app_name="Test App",
        app_version="0.1.0",
        environment="test",
        data_dir=workspace_tmp_path / "data",
        upload_dir=workspace_tmp_path / "data" / "uploads",
        export_dir=workspace_tmp_path / "data" / "exports",
        database_url=f"sqlite:///{workspace_tmp_path / 'data' / 'app.db'}",
        provider_mode="local",
    )

    settings.ensure_local_directories()

    assert settings.data_dir.exists()
    assert settings.upload_dir.exists()
    assert settings.export_dir.exists()


def test_settings_load_environment_overrides(monkeypatch) -> None:
    monkeypatch.setenv("APP_NAME", "Research Assistant Test")
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATA_DIR", "custom_data")
    monkeypatch.setenv("UPLOAD_DIR", "custom_uploads")
    monkeypatch.setenv("EXPORT_DIR", "custom_exports")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///custom_data/test.db")
    monkeypatch.setenv("PROVIDER_MODE", "ollama")
    monkeypatch.setenv("MAX_UPLOAD_FILE_SIZE_BYTES", "1024")

    settings = Settings.from_env()

    assert settings.app_name == "Research Assistant Test"
    assert settings.environment == "test"
    assert settings.data_dir.name == "custom_data"
    assert settings.upload_dir.name == "custom_uploads"
    assert settings.export_dir.name == "custom_exports"
    assert settings.database_url.startswith("sqlite:///")
    assert settings.database_url.endswith("custom_data/test.db")
    assert settings.provider_mode == "ollama"
    assert settings.max_upload_file_size_bytes == 1024


def test_settings_reject_invalid_database_url(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/app")

    try:
        Settings.from_env()
    except ValueError as exc:
        assert "Only sqlite" in str(exc)
    else:
        raise AssertionError("Expected ValueError for non-sqlite DATABASE_URL")


def test_settings_reject_empty_provider_mode(monkeypatch) -> None:
    monkeypatch.setenv("PROVIDER_MODE", " ")

    try:
        Settings.from_env()
    except ValueError as exc:
        assert "PROVIDER_MODE cannot be empty" in str(exc)
    else:
        raise AssertionError("Expected ValueError for empty PROVIDER_MODE")


def test_settings_reject_invalid_upload_size(monkeypatch) -> None:
    monkeypatch.setenv("MAX_UPLOAD_FILE_SIZE_BYTES", "0")

    try:
        Settings.from_env()
    except ValueError as exc:
        assert "MAX_UPLOAD_FILE_SIZE_BYTES must be a positive integer" in str(exc)
    else:
        raise AssertionError("Expected ValueError for invalid MAX_UPLOAD_FILE_SIZE_BYTES")
