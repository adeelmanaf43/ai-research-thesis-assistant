from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import os
from urllib.parse import urlparse

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - keeps global environments usable before install.
    load_dotenv = None


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_APP_NAME = "AI Research / Thesis Assistant"
DEFAULT_APP_VERSION = "0.1.0"
DEFAULT_ENVIRONMENT = "local"
DEFAULT_PROVIDER_MODE = "local"
SQLITE_PREFIX = "sqlite:///"


def _sqlite_url(path: Path) -> str:
    return f"{SQLITE_PREFIX}{path.as_posix()}"


def _path_from_env(name: str, default: Path) -> Path:
    raw_value = os.getenv(name)
    path = Path(raw_value) if raw_value else default
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def _database_url_from_env(data_dir: Path) -> str:
    raw_value = os.getenv("DATABASE_URL")
    if not raw_value:
        return _sqlite_url(data_dir / "app.db")

    if raw_value.startswith(SQLITE_PREFIX):
        parsed_path = Path(raw_value.removeprefix(SQLITE_PREFIX))
        if parsed_path.is_absolute():
            return _sqlite_url(parsed_path)
        return _sqlite_url(PROJECT_ROOT / parsed_path)

    parsed = urlparse(raw_value)
    if parsed.scheme:
        raise ValueError("Only sqlite:/// database URLs are supported in the local-first MVP.")
    raise ValueError("DATABASE_URL must use the sqlite:/// URL format.")


def _provider_mode_from_env() -> str:
    provider_mode = os.getenv("PROVIDER_MODE", DEFAULT_PROVIDER_MODE).strip().lower()
    if not provider_mode:
        raise ValueError("PROVIDER_MODE cannot be empty.")
    return provider_mode


@dataclass(frozen=True)
class Settings:
    app_name: str
    app_version: str
    environment: str
    data_dir: Path
    upload_dir: Path
    export_dir: Path
    database_url: str
    provider_mode: str

    @classmethod
    def from_env(cls) -> "Settings":
        if load_dotenv is not None:
            load_dotenv(PROJECT_ROOT / ".env")

        data_dir = _path_from_env("DATA_DIR", PROJECT_ROOT / "data")
        upload_dir = _path_from_env("UPLOAD_DIR", data_dir / "uploads")
        export_dir = _path_from_env("EXPORT_DIR", data_dir / "exports")
        return cls(
            app_name=os.getenv("APP_NAME", DEFAULT_APP_NAME),
            app_version=os.getenv("APP_VERSION", DEFAULT_APP_VERSION),
            environment=os.getenv("APP_ENV", DEFAULT_ENVIRONMENT),
            data_dir=data_dir,
            upload_dir=upload_dir,
            export_dir=export_dir,
            database_url=_database_url_from_env(data_dir),
            provider_mode=_provider_mode_from_env(),
        )

    def ensure_local_directories(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.export_dir.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings.from_env()
    settings.ensure_local_directories()
    return settings
