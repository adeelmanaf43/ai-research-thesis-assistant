from pathlib import Path
import sqlite3

from backend.app.core.config import Settings, get_settings


SQLITE_PREFIX = "sqlite:///"


def sqlite_path_from_url(database_url: str) -> Path:
    if not database_url.startswith(SQLITE_PREFIX):
        raise ValueError("Only sqlite:/// database URLs are supported in the local-first MVP.")
    return Path(database_url.removeprefix(SQLITE_PREFIX))


def get_connection(settings: Settings | None = None) -> sqlite3.Connection:
    active_settings = settings or get_settings()
    database_path = sqlite_path_from_url(active_settings.database_url)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    return connection

