from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from backend.app.core.config import SQLITE_PREFIX, Settings, get_settings


class Base(DeclarativeBase):
    """Base class for future SQLAlchemy models."""


def sqlite_path_from_url(database_url: str) -> Path:
    if not database_url.startswith(SQLITE_PREFIX):
        raise ValueError("Only sqlite:/// database URLs are supported in the local-first MVP.")
    return Path(database_url.removeprefix(SQLITE_PREFIX))


def create_database_engine(settings: Settings | None = None) -> Engine:
    active_settings = settings or get_settings()
    database_path = sqlite_path_from_url(active_settings.database_url)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(
        active_settings.database_url,
        connect_args={"check_same_thread": False},
    )


engine = create_database_engine()
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


def get_session_factory(database_engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(
        bind=database_engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_database(database_engine: Engine | None = None) -> None:
    import backend.app.models  # noqa: F401

    active_engine = database_engine or engine
    Base.metadata.create_all(bind=active_engine)
    _ensure_sqlite_schema_compatibility(active_engine)


def _ensure_sqlite_schema_compatibility(database_engine: Engine) -> None:
    if database_engine.dialect.name != "sqlite":
        return

    inspector = inspect(database_engine)
    if "documents" not in inspector.get_table_names():
        return

    document_columns = {column["name"] for column in inspector.get_columns("documents")}
    if "extraction_error" in document_columns:
        return

    with database_engine.begin() as connection:
        connection.execute(text("ALTER TABLE documents ADD COLUMN extraction_error TEXT"))
