from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import os

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - keeps global environments usable before install.
    load_dotenv = None


PROJECT_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class Settings:
    app_name: str
    app_version: str
    environment: str
    data_dir: Path
    upload_dir: Path
    database_url: str

    @classmethod
    def from_env(cls) -> "Settings":
        if load_dotenv is not None:
            load_dotenv(PROJECT_ROOT / ".env")

        data_dir = Path(os.getenv("DATA_DIR", PROJECT_ROOT / "data"))
        upload_dir = Path(os.getenv("UPLOAD_DIR", data_dir / "uploads"))
        return cls(
            app_name=os.getenv("APP_NAME", "AI Research / Thesis Assistant"),
            app_version=os.getenv("APP_VERSION", "0.1.0"),
            environment=os.getenv("APP_ENV", "local"),
            data_dir=data_dir,
            upload_dir=upload_dir,
            database_url=os.getenv("DATABASE_URL", f"sqlite:///{data_dir / 'app.db'}"),
        )

    def ensure_local_directories(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.upload_dir.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings.from_env()
    settings.ensure_local_directories()
    return settings
